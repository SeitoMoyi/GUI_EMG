"""Main application file for EMG data streaming and recording."""

import os
import numpy as np
from flask import Flask, render_template, jsonify, request
import threading
import traceback
import datetime
from config import DEFAULT_SAVE_DIRECTORY, NUM_SENSORS, SAMPLING_RATE
from utils import select_save_directory, load_muscle_labels
from state_manager import ApplicationState


app = Flask(__name__)

# Let user select save directory before starting
try:
    SAVE_DIRECTORY = select_save_directory()
    print(f"Recordings will be saved to: {os.path.abspath(SAVE_DIRECTORY)}")
except Exception as e:
    print(f"Error selecting directory: {e}")
    SAVE_DIRECTORY = DEFAULT_SAVE_DIRECTORY
    os.makedirs(SAVE_DIRECTORY, exist_ok=True)

# Initialize application state
app_state = ApplicationState()


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
            success, message = app_state.start_delsys_streaming()
            return jsonify({'success': success, 'message': message, 'streaming': success})
        elif action == 'stop':
            success, message = app_state.stop_delsys_streaming()
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
        if app_state.is_recording_flag:
            # Currently recording - stop it
            success, message = app_state.stop_delsys_recording()
            return jsonify({'success': success, 'message': message, 'recording': False})
        else:
            # Not recording - start it
            success, message = app_state.start_recording_segment()
            return jsonify({'success': success, 'message': message, 'recording': success})
    except Exception as e:
        print(f"❌ Error in toggle_recording route: {e}")
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Error: {str(e)}', 'recording': False})


@app.route('/live_data')
def live_data():
    try:
        with app_state.live_data_lock:
            data_chunks = []
            labels = []
            for i in range(NUM_SENSORS):
                channel_chunks = []
                for chunk_dict in app_state.live_data_buffers[i]:
                    channel_chunks.extend(chunk_dict['samples'])
                data_chunks.append(channel_chunks)
                if app_state.live_data_buffers[i] and len(app_state.live_data_buffers[i]) > 0:
                    labels.append(app_state.live_data_buffers[i][-1]['label'])
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
            'is_recording': app_state.is_recording_flag,
            'handler_exists': app_state.handler is not None,
            'handler_streaming': app_state.handler.streaming if app_state.handler else False,
            'buffer_sizes': [len(buf) for buf in app_state.recording_data_buffer],
            'save_directory': SAVE_DIRECTORY,
            'trial_counter': app_state.trial_counter,
            'session_start_time': app_state.recording_session_start_time.isoformat() if app_state.recording_session_start_time else None,
            'system_time': datetime.datetime.now().isoformat(),
            'buffer_capacity': app_state.LIVE_BUFFER_CHUNKS,
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
        print(f"📊 Using {NUM_SENSORS} channels")

        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    except Exception as e:
        print(f"❌ Error starting Flask server: {e}")
        traceback.print_exc()
    finally:
        print("🛑 Flask server shutting down...")
        # Attempt to stop streaming cleanly
        if app_state.handler:
            try:
                app_state.handler.stop_streaming()
            except Exception as e:
                print(f"Error stopping handler on shutdown: {e}")