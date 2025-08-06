"""State management for the EMG application."""

import threading
import collections
import time
import queue
import datetime
from config import NUM_SENSORS, SAMPLING_RATE
from delsys import DelsysDataHandler


class ApplicationState:
    """Manages the application state including streaming, recording, and data buffering."""
    
    def __init__(self):
        # Global State
        self.handler = None
        self.recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
        self.recording_lock = threading.Lock()
        self.is_recording_flag = False
        self.start_time = None

        # Recording Session Info
        self.recording_session_start_time = None
        self.trial_counter = 1

        # Live Data Buffering for GUI
        self.LIVE_BUFFER_CHUNKS = 6000
        self.live_data_buffers = [collections.deque(maxlen=self.LIVE_BUFFER_CHUNKS) for _ in range(NUM_SENSORS)]
        self.live_data_lock = threading.Lock()
        
    def recording_worker(self):
        """Worker thread to read data from the handler's queue continuously."""
        local_sample_count = 0
        print("🔄 Recording/Streaming worker started.")
        try:
            while self.handler and self.handler.streaming:
                try:
                    processed_data = self.handler.output_queue.get(timeout=1.0)
                    channel_id = processed_data['channel']
                    samples = processed_data['samples']
                    muscle_label = processed_data.get('muscle_label', f'Ch{channel_id}')

                    # Only process data for the first NUM_SENSORS channels
                    if channel_id >= NUM_SENSORS:
                        continue

                    # Always update live data buffers for visualization
                    with self.live_data_lock:
                        self.live_data_buffers[channel_id].append({
                            'samples': samples.tolist(),
                            'label': muscle_label
                        })

                    # Conditionally record data based on is_recording_flag
                    with self.recording_lock:
                        if self.is_recording_flag:
                            self.recording_data_buffer[channel_id + 1].extend(samples)
                            local_sample_count += len(samples)
                            # Set start_time for the recording segment only
                            if self.start_time is None and local_sample_count == len(samples):
                                self.start_time = time.time()
                                print(f"📍 Recording segment start time set: {self.start_time}")

                    # Debug: Print first few samples with more context
                    if local_sample_count < 100 and self.is_recording_flag:
                        timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
                        print(f"[{timestamp}] 📏 Recording Ch{channel_id+1}/{NUM_SENSORS}: {samples[0]:.6f} V ({muscle_label}) | Sample count: {local_sample_count}")
                    elif local_sample_count == 100 and self.is_recording_flag:
                        print(f"Suppressing further recording debug prints for this segment (Ch{channel_id})...")

                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"❌ Error in recording worker loop: {e}")
                    continue
        except Exception as e:
            print(f"❌ Unexpected error in recording worker: {e}")
        finally:
            print("🔄 Recording/Streaming worker stopped.")

    def start_delsys_streaming(self):
        """Starts the Delsys data handler and the continuous worker thread."""
        try:
            # Clear buffers at the very beginning of a new streaming session
            with self.recording_lock:
                for i in range(len(self.recording_data_buffer)):
                    self.recording_data_buffer[i].clear()
            self.start_time = None
            with self.live_data_lock:
                for buffer in self.live_data_buffers:
                    buffer.clear()

            # Stop existing handler if running
            if self.handler is not None:
                try:
                    print("🛑 Stopping existing handler before starting new stream...")
                    self.handler.stop_streaming()
                except Exception as e:
                    print(f"Warning: Error stopping previous handler: {e}")
                self.handler = None

            # Reset recording state
            self.is_recording_flag = False

            # Initialize session time and trial counter for new session
            self.recording_session_start_time = datetime.datetime.now()
            self.trial_counter = 1
            print(f"🚀 Starting Delsys handler")

            # Create new handler instance
            self.handler = DelsysDataHandler(host_ip='127.0.0.1', num_sensors=16,
                                          sampling_rate=SAMPLING_RATE, envelope=False)

            # Attempt to start streaming
            if self.handler.start_streaming():
                # Start the worker thread *after* successful streaming start
                worker_thread = threading.Thread(target=self.recording_worker, daemon=True)
                worker_thread.start()
                return True, "Streaming started successfully."
            else:
                # Failed to start streaming
                if self.handler:
                    try:
                        self.handler.stop_streaming()
                    except:
                        pass
                    self.handler = None
                return False, "Failed to start Delsys streaming. Check if Dragonfly is running and configured correctly."

        except Exception as e:
            print(f"❌ Error starting streaming: {e}")
            # Ensure cleanup on error
            if self.handler:
                try:
                    self.handler.stop_streaming()
                except:
                    pass
                self.handler = None
            return False, f"Error starting streaming: {str(e)}"

    def stop_delsys_streaming(self):
        """Stops the Delsys data handler streaming."""
        try:
            # Ensure any ongoing recording is stopped first
            if self.is_recording_flag:
                print("⚠️ Stopping recording before stopping stream...")
                self.stop_delsys_recording()

            with self.recording_lock:
                # Signal to stop streaming
                if self.handler and self.handler.streaming:
                    print("🛑 Stopping Delsys handler streaming...")
                    self.handler.stop_streaming()
                    self.handler = None
                else:
                    print("⚠️ Handler was not streaming or already stopped.")
                    if self.handler:
                        self.handler = None

                # Reset states regardless
                self.is_recording_flag = False
                # Clear buffers
                self.recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
                self.start_time = None
                # Clear live buffers
                with self.live_data_lock:
                    for buffer in self.live_data_buffers:
                        buffer.clear()

            return True, "Streaming stopped successfully."

        except Exception as e:
            print(f"❌ Error stopping streaming: {e}")
            # Force cleanup in case of error
            if self.handler:
                try:
                    self.handler.stop_streaming()
                except Exception as cleanup_e:
                    print(f"Error during cleanup stop: {cleanup_e}")
                self.handler = None
            self.is_recording_flag = False
            with self.recording_lock:
                self.recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
                self.start_time = None
            with self.live_data_lock:
                for buffer in self.live_data_buffers:
                    buffer.clear()
            return False, f"Error stopping streaming: {str(e)}"

    def start_recording_segment(self):
        """Starts recording data into the buffer."""
        try:
            with self.recording_lock:
                if self.is_recording_flag:
                    return False, "Recording already in progress for this segment."
                if not self.handler or not self.handler.streaming:
                    return False, "Streaming is not active. Start streaming first."

                # Clear buffers for the new recording segment
                for i in range(len(self.recording_data_buffer)):
                    self.recording_data_buffer[i].clear()
                self.start_time = None

                self.is_recording_flag = True
                print(f"⏺️ Recording segment started (Trial #{self.trial_counter}).")
                return True, f"Recording segment started (Trial #{self.trial_counter})."
        except Exception as e:
            print(f"❌ Error starting recording segment: {e}")
            return False, f"Error starting recording: {str(e)}"

    def stop_delsys_recording(self):
        """Stops the recording segment and saves the data."""
        from data_handler import save_emg_recording
        from utils import load_muscle_labels
        
        try:
            with self.recording_lock:
                if not self.is_recording_flag:
                    return False, "No recording segment in progress."
                self.is_recording_flag = False
                print("🛑 Recording flag set to False for current segment.")

            time.sleep(0.1)

            # Load muscle labels from YAML configuration file
            muscle_labels = load_muscle_labels()

            # Save data for the completed segment
            success, message, min_samples = save_emg_recording(
                save_directory='./recordings',
                recording_data_buffer=self.recording_data_buffer,
                start_time=self.start_time,
                sampling_rate=SAMPLING_RATE,
                muscle_labels=muscle_labels,
                recording_session_start_time=self.recording_session_start_time,
                trial_counter=self.trial_counter
            )

            # Clear buffers for next segment
            with self.recording_lock:
                self.recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
                self.start_time = None

            if success:
                print(f"✅ Recording segment #{self.trial_counter} saved successfully ({min_samples} samples).")
                self.trial_counter += 1
                return True, f"Recording segment #{self.trial_counter - 1} saved successfully ({min_samples} samples)."
            else:
                print(f"❌ Error saving recording segment #{self.trial_counter}: {message}")
                return False, f"Error saving recording: {message}"

        except Exception as e:
            print(f"❌ Error stopping recording segment: {e}")
            with self.recording_lock:
                self.recording_data_buffer = [[] for _ in range(NUM_SENSORS + 1)]
                self.start_time = None
            return False, f"Error stopping recording: {str(e)}"