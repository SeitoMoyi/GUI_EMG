# app.py - EMG Data Streaming and Recording Application

import os
import numpy as np
from flask import Flask, render_template, jsonify, request
from delsys_handler import DelsysDataHandler
from emg_data_saver import save_emg_recording
import threading
import time
import collections
import datetime
import queue
import tkinter as tk
from tkinter import filedialog
import sys
import traceback
import yaml

def select_save_directory():
    """Open a dialog to select the save directory before starting the app."""
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)
    save_dir = filedialog.askdirectory(
        title="Select directory to save EMG recordings",
        initialdir="./recordings"
    )
    root.destroy()
    if not save_dir:
        print("No directory selected. Using default './recordings'")
        save_dir = "./recordings"
        os.makedirs(save_dir, exist_ok=True)
    return save_dir

app = Flask(__name__)

# Configuration
HOST_IP = '127.0.0.1'
NUM_SENSORS = 4
SAMPLING_RATE = 2000.0

# Let user select save directory before starting
try:
    SAVE_DIRECTORY = select_save_directory()
    print(f"Recordings will be saved to: {os.path.abspath(SAVE_DIRECTORY)}")
except Exception as e:
    print(f"Error selecting directory: {e}")
    SAVE_DIRECTORY = "./recordings"
    os.makedirs(SAVE_DIRECTORY, exist_ok=True)

# Global State
handler = None
recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
recording_lock = threading.Lock()
is_recording_flag = False
start_time = None

# Recording Session Info
recording_session_start_time = None
trial_counter = 1

# Live Data Buffering for GUI
LIVE_BUFFER_CHUNKS = 6000
live_data_buffers = [collections.deque(maxlen=LIVE_BUFFER_CHUNKS) for _ in range(NUM_SENSORS)]
live_data_lock = threading.Lock()

# Helper Functions

def recording_worker():
    """Worker thread to read data from the handler's queue continuously."""
    global is_recording_flag, recording_data_buffer, start_time, live_data_buffers, handler
    local_sample_count = 0
    print("🔄 Recording/Streaming worker started.")
    try:
        while handler and handler.streaming:
            try:
                processed_data = handler.output_queue.get(timeout=1.0)
                channel_id = processed_data['channel']
                samples = processed_data['samples']
                muscle_label = processed_data.get('muscle_label', f'Ch{channel_id}')

                # Only process data for the first NUM_SENSORS channels
                if channel_id >= NUM_SENSORS:
                    continue

                # Always update live data buffers for visualization
                with live_data_lock:
                    live_data_buffers[channel_id].append({
                        'samples': samples.tolist(),
                        'label': muscle_label
                    })

                # Conditionally record data based on is_recording_flag
                with recording_lock:
                    if is_recording_flag:
                        recording_data_buffer[channel_id + 1].extend(samples)
                        local_sample_count += len(samples)
                        # Set start_time for the recording segment only
                        if start_time is None and local_sample_count == len(samples):
                            start_time = time.time()
                            print(f"📍 Recording segment start time set: {start_time}")

                # Debug: Print first few samples with more context
                if local_sample_count < 100 and is_recording_flag:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                    print(f"[{timestamp}] 📏 Recording Ch{channel_id+1}/{NUM_SENSORS}: {samples[0]:.6f} V ({muscle_label}) | Sample count: {local_sample_count}")
                elif local_sample_count == 100 and is_recording_flag:
                    print(f"Suppressing further recording debug prints for this segment (Ch{channel_id})...")

            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error in recording worker loop: {e}")
                traceback.print_exc()
                continue
    except Exception as e:
        print(f"❌ Unexpected error in recording worker: {e}")
        traceback.print_exc()
    finally:
        print("🔄 Recording/Streaming worker stopped.")

def start_delsys_streaming():
    """Starts the Delsys data handler and the continuous worker thread."""
    global handler, is_recording_flag, recording_data_buffer, start_time, live_data_buffers, recording_session_start_time, trial_counter
    try:
        # Clear buffers at the very beginning of a new streaming session
        with recording_lock:
            for i in range(len(recording_data_buffer)):
                recording_data_buffer[i].clear()
        start_time = None
        with live_data_lock:
             for buffer in live_data_buffers:
                 buffer.clear()

        # Stop existing handler if running
        if handler is not None:
            try:
                print("🛑 Stopping existing handler before starting new stream...")
                handler.stop_streaming()
            except Exception as e:
                print(f"Warning: Error stopping previous handler: {e}")
            handler = None

        # Reset recording state
        is_recording_flag = False

        # Initialize session time and trial counter for new session
        recording_session_start_time = datetime.datetime.now()
        trial_counter = 1
        print(f"🚀 Starting Delsys handler with IP: {HOST_IP}")

        # Create new handler instance
        handler = DelsysDataHandler(host_ip=HOST_IP, num_sensors=16,
                                  sampling_rate=SAMPLING_RATE, envelope=False)

        # Attempt to start streaming
        if handler.start_streaming():
            # Start the worker thread *after* successful streaming start
            worker_thread = threading.Thread(target=recording_worker, daemon=True)
            worker_thread.start()
            return True, "Streaming started successfully."
        else:
            # Failed to start streaming
            if handler:
                try:
                    handler.stop_streaming()
                except:
                    pass
                handler = None
            return False, "Failed to start Delsys streaming. Check if Dragonfly is running and configured correctly."

    except Exception as e:
        print(f"❌ Error starting streaming: {e}")
        traceback.print_exc()
        # Ensure cleanup on error
        if handler:
            try:
                handler.stop_streaming()
            except:
                pass
            handler = None
        return False, f"Error starting streaming: {str(e)}"


def stop_delsys_streaming():
    """Stops the Delsys data handler streaming."""
    global handler, is_recording_flag, recording_data_buffer, start_time
    try:
        # Ensure any ongoing recording is stopped first
        if is_recording_flag:
             print("⚠️ Stopping recording before stopping stream...")
             stop_delsys_recording()

        with recording_lock:
            # Signal to stop streaming
            if handler and handler.streaming:
                 print("🛑 Stopping Delsys handler streaming...")
                 handler.stop_streaming()
                 handler = None
            else:
                 print("⚠️ Handler was not streaming or already stopped.")
                 if handler:
                     handler = None

            # Reset states regardless
            is_recording_flag = False
            # Clear buffers
            recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
            start_time = None
            # Clear live buffers
            with live_data_lock:
                 for buffer in live_data_buffers:
                     buffer.clear()

        return True, "Streaming stopped successfully."

    except Exception as e:
        print(f"❌ Error stopping streaming: {e}")
        traceback.print_exc()
        # Force cleanup in case of error
        if handler:
            try:
                handler.stop_streaming()
            except Exception as cleanup_e:
                print(f"Error during cleanup stop: {cleanup_e}")
            handler = None
        is_recording_flag = False
        with recording_lock:
             recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
             start_time = None
        with live_data_lock:
             for buffer in live_data_buffers:
                 buffer.clear()
        return False, f"Error stopping streaming: {str(e)}"


def start_recording_segment():
    """Starts recording data into the buffer."""
    global is_recording_flag, recording_data_buffer, start_time, trial_counter
    try:
        with recording_lock:
            if is_recording_flag:
                return False, "Recording already in progress for this segment."
            if not handler or not handler.streaming:
                 return False, "Streaming is not active. Start streaming first."

            # Clear buffers for the new recording segment
            for i in range(len(recording_data_buffer)):
                recording_data_buffer[i].clear()
            start_time = None

            is_recording_flag = True
            print(f"⏺️ Recording segment started (Trial #{trial_counter}).")
            return True, f"Recording segment started (Trial #{trial_counter})."
    except Exception as e:
        print(f"❌ Error starting recording segment: {e}")
        traceback.print_exc()
        return False, f"Error starting recording: {str(e)}"

def stop_delsys_recording():
    """Stops the recording segment and saves the data."""
    global is_recording_flag, recording_data_buffer, start_time, trial_counter, recording_session_start_time
    try:
        with recording_lock:
            if not is_recording_flag:
                return False, "No recording segment in progress."
            is_recording_flag = False
            print("🛑 Recording flag set to False for current segment.")

        time.sleep(0.1)

        # Load muscle labels from YAML configuration file
        muscle_labels = load_muscle_labels()

        # Save data for the completed segment
        success, message, min_samples = save_emg_recording(
            save_directory=SAVE_DIRECTORY,
            recording_data_buffer=recording_data_buffer,
            start_time=start_time,
            sampling_rate=SAMPLING_RATE,
            muscle_labels=muscle_labels,
            recording_session_start_time=recording_session_start_time,
            trial_counter=trial_counter
        )

        # Clear buffers for next segment
        with recording_lock:
            recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
            start_time = None

        if success:
            print(f"✅ Recording segment #{trial_counter} saved successfully ({min_samples} samples).")
            trial_counter += 1
            return True, f"Recording segment #{trial_counter - 1} saved successfully ({min_samples} samples)."
        else:
            print(f"❌ Error saving recording segment #{trial_counter}: {message}")
            return False, f"Error saving recording: {message}"

    except Exception as e:
        print(f"❌ Error stopping recording segment: {e}")
        traceback.print_exc()
        with recording_lock:
            recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
            start_time = None
        return False, f"Error stopping recording: {str(e)}"

def load_muscle_labels():
    """Load muscle labels from YAML configuration file."""
    try:
        import os
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'muscle_labels.yaml')
        print(f"🔍 Looking for muscle labels file at: {yaml_path}")
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            muscle_labels = config.get('muscle_labels', ['L-TIBI', 'L-GAST', 'L-RECT', 'R-TIBI'])[:NUM_SENSORS]
            print(f"✅ Loaded muscle labels: {muscle_labels}")
            return muscle_labels
    except FileNotFoundError:
        print("⚠️  muscle_labels.yaml not found. Using default labels.")
        return ['L-TIBI', 'L-GAST', 'L-RECT', 'R-TIBI']
    except Exception as e:
        print(f"❌ Error loading muscle labels: {e}. Using default labels.")
        return ['L-TIBI', 'L-GAST', 'L-RECT', 'R-TIBI']

# Flask Routes

@app.route('/')
def index():
    try:
        # Load labels from YAML configuration file
        labels = load_muscle_labels()
        print(f"📤 Sending muscle labels to template: {labels}")
        return render_template('index.html', num_sensors=NUM_SENSORS, muscle_labels=labels)
    except Exception as e:
        print(f"❌ Error in index route: {e}")
        traceback.print_exc()
        return f"Error loading page: {str(e)}", 500

# Endpoint to start/stop the persistent streaming
@app.route('/toggle_streaming', methods=['POST'])
def toggle_streaming():
    try:
         data = request.get_json()
         action = data.get('action', '').lower() if data else ''

         if action == 'start':
             success, message = start_delsys_streaming()
             return jsonify({'success': success, 'message': message, 'streaming': success})
         elif action == 'stop':
             success, message = stop_delsys_streaming()
             return jsonify({'success': success, 'message': message, 'streaming': not success})
         else:
             return jsonify({'success': False, 'message': 'Invalid action. Use "start" or "stop".'})

    except Exception as e:
        print(f"❌ Error in toggle_streaming route: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# Modified to handle click-to-record toggle
@app.route('/toggle_recording', methods=['POST'])
def toggle_recording():
    try:
        global is_recording_flag
        
        if is_recording_flag:
            # Currently recording - stop it
            success, message = stop_delsys_recording()
            return jsonify({'success': success, 'message': message, 'recording': False})
        else:
            # Not recording - start it
            success, message = start_recording_segment()
            return jsonify({'success': success, 'message': message, 'recording': success})
    except Exception as e:
        print(f"❌ Error in toggle_recording route: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}', 'recording': False})

@app.route('/live_data')
def live_data():
    try:
        with live_data_lock:
            data_chunks = []
            labels = []
            for i in range(NUM_SENSORS):
                channel_chunks = []
                for chunk_dict in live_data_buffers[i]:
                    channel_chunks.extend(chunk_dict['samples'])
                data_chunks.append(channel_chunks)
                if live_data_buffers[i] and len(live_data_buffers[i]) > 0:
                    labels.append(live_data_buffers[i][-1]['label'])
                else:
                    # Use muscle labels from the YAML config if available
                    try:
                        muscle_labels = load_muscle_labels()
                        if i < len(muscle_labels):
                            labels.append(muscle_labels[i])
                        else:
                            labels.append(f'Ch{i}')
                    except:
                        labels.append(f'Ch{i}')
            print(f"📤 Sending live data with labels: {labels}")  # Debug line
        return jsonify({'data': data_chunks, 'labels': labels})
    except Exception as e:
        print(f"❌ Error fetching live data: {e}")
        traceback.print_exc()
        # Return empty data on error to prevent frontend breakage
        return jsonify({'data': [[] for _ in range(NUM_SENSORS)], 'labels': [f'Ch{i}' for i in range(NUM_SENSORS)]})

@app.route('/status')
def status():
    """Debug endpoint to check system status"""
    try:
        status_info = {
            'is_recording': is_recording_flag,
            'handler_exists': handler is not None,
            'handler_streaming': handler.streaming if handler else False,
            'buffer_sizes': [len(buf) for buf in recording_data_buffer],
            'save_directory': SAVE_DIRECTORY,
            'trial_counter': trial_counter,
            'session_start_time': recording_session_start_time.isoformat() if recording_session_start_time else None,
            'system_time': datetime.datetime.now().isoformat(),
            'buffer_capacity': LIVE_BUFFER_CHUNKS,
            'sampling_rate': SAMPLING_RATE,
            'active_channels': NUM_SENSORS
        }
        return jsonify(status_info)
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    try:
        print("🚀 Starting Flask server...")
        print(f"📁 Recordings will be saved to: {os.path.abspath(SAVE_DIRECTORY)}")
        print(f"🌐 Server will be available at: http://localhost:5000")
        print("⚠️  Make sure Dragonfly is running and configured for ports 50040/50041")
        print("💡 You will need to click 'Start Streaming' in the UI to begin.")
        print(f"📊 Using {NUM_SENSORS} channels: L-TIBI, L-GAST, L-RECT, R-TIBI")

        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        traceback.print_exc()
    finally:
        print("🛑 Flask server shutting down...")
        # Attempt to stop streaming cleanly
        if handler:
            try:
                handler.stop_streaming()
            except Exception as e:
                print(f"Error stopping handler on shutdown: {e}")