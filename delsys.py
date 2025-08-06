"""Delsys Trigno system handler for EMG data streaming."""

import socket
import struct
import threading
import time
import numpy as np
import queue
from scipy import signal

from config import (
    EMG_COMMAND_PORT, 
    EMG_STREAM_PORT, 
    ACTIVE_CHANNELS, 
    SAMPLING_RATE,
    NOTCH_FREQ,
    NOTCH_Q,
    HP_FREQ
)
from utils import load_muscle_labels


class DelsysDataHandler:
    """
    Handles connection and data streaming from Delsys Trigno system
    using the same protocol as the working Kivy app.
    Updated for 4 channel operation.
    """
    
    def __init__(self, host_ip='127.0.0.1', num_sensors=16, sampling_rate=SAMPLING_RATE, envelope=False):
        self.host_ip = host_ip
        self.num_sensors = num_sensors
        self.active_channels = ACTIVE_CHANNELS
        self.sampling_rate = sampling_rate
        self.envelope = envelope
        
        # Socket configuration matching working app
        self.EMG_COMMAND_PORT = EMG_COMMAND_PORT
        self.EMG_STREAM_PORT = EMG_STREAM_PORT
        
        self.command_socket = None
        self.stream_socket = None
        self.streaming = False
        self.stream_thread = None
        
        # Output queue for processed data
        self.output_queue = queue.Queue(maxsize=1000)
        
        # Signal processing elements
        self._design_filters()
        self._initialize_filter_states()
        
        # Load muscle labels from YAML configuration file
        self.muscle_labels = load_muscle_labels()
        
    def _design_filters(self):
        """Design the filters needed for signal processing"""
        # Design 60Hz notch filter
        self.notch_freq = NOTCH_FREQ
        Q = NOTCH_Q  # Quality factor for the notch filter
        b, a = signal.iirnotch(self.notch_freq, Q, self.sampling_rate)
        self.notch_b = b
        self.notch_a = a
        
        # Design DC removal filter (High-pass at 0.5Hz)
        self.hp_freq = HP_FREQ
        hp_b, hp_a = signal.butter(2, self.hp_freq / (self.sampling_rate / 2), 'high')
        self.dc_block_b = hp_b
        self.dc_block_a = hp_a
    
    def _initialize_filter_states(self):
        """Initialize filter states for each channel"""
        self.notch_zi = {}
        self.dc_block_zi = {}
        for ch in range(self.active_channels):
            # Initialize filter states to zero
            self.notch_zi[ch] = signal.lfilter_zi(self.notch_b, self.notch_a)
            self.dc_block_zi[ch] = signal.lfilter_zi(self.dc_block_b, self.dc_block_a)
    
    def _process_emg_sample(self, sample_value, channel_id):
        """Apply signal processing to a single EMG sample"""
        # Apply DC removal (high-pass filter)
        dc_removed, self.dc_block_zi[channel_id] = signal.lfilter(
            self.dc_block_b, self.dc_block_a, [sample_value], zi=self.dc_block_zi[channel_id]
        )
        dc_removed = dc_removed[0]
        
        # Apply 60Hz notch filter
        notched, self.notch_zi[channel_id] = signal.lfilter(
            self.notch_b, self.notch_a, [dc_removed], zi=self.notch_zi[channel_id]
        )
        notched = notched[0]
        
        # Apply rectification
        rectified = abs(notched)
        
        return rectified
        
    def start_streaming(self):
        """Start the EMG data streaming"""
        try:
            print(f"Connecting to Delsys system at {self.host_ip}")
            
            # Create command socket
            self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_socket.settimeout(10.0)
            self.command_socket.connect((self.host_ip, self.EMG_COMMAND_PORT))
            print(f"Command socket connected to port {self.EMG_COMMAND_PORT}")
            
            # Create stream socket
            self.stream_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.stream_socket.settimeout(10.0)
            self.stream_socket.connect((self.host_ip, self.EMG_STREAM_PORT))
            print(f"Stream socket connected to port {self.EMG_STREAM_PORT}")
            
            # Send start commands (matching working app)
            self.command_socket.sendall(b'START')
            print("Sent START command")
            
            self.command_socket.sendall(b'TRIGGER START\r\n\r\n')
            print("Sent TRIGGER START command")
            
            # Start streaming thread
            self.streaming = True
            self.stream_thread = threading.Thread(target=self._stream_worker, daemon=True)
            self.stream_thread.start()
            
            print(f"✅ Delsys streaming started successfully (processing {self.active_channels} channels)")
            return True
            
        except Exception as e:
            print(f"❌ Error starting Delsys streaming: {e}")
            self.stop_streaming()
            return False
    
    def _stream_worker(self):
        """Worker thread to continuously read EMG data"""
        print("🔄 EMG stream worker started")
        
        try:
            while self.streaming and self.stream_socket:
                try:
                    # Read 64 bytes (16 floats) as per protocol
                    emg_byte_data = self.stream_socket.recv(64)
                    
                    if len(emg_byte_data) != 64:
                        print(f"Warning: Received {len(emg_byte_data)} bytes, expected 64")
                        continue
                    
                    # Unpack as 16 little-endian floats
                    emg_data = struct.unpack('<16f', emg_byte_data)
                    
                    # Process only the first 4 channels
                    for channel_id in range(self.active_channels):
                        sample_value = emg_data[channel_id]
                        
                        # Apply signal processing
                        processed_value = self._process_emg_sample(sample_value, channel_id)
                        
                        # Create processed data packet
                        processed_data = {
                            'channel': channel_id,
                            'samples': np.array([processed_value], dtype=np.float64),
                            'muscle_label': self.muscle_labels[channel_id] if channel_id < len(self.muscle_labels) else f'Ch{channel_id}',
                            'timestamp': time.time()
                        }
                        
                        # Add to output queue (non-blocking)
                        try:
                            self.output_queue.put_nowait(processed_data)
                        except queue.Full:
                            # Remove oldest item and add new one
                            try:
                                self.output_queue.get_nowait()
                                self.output_queue.put_nowait(processed_data)
                            except queue.Empty:
                                pass
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.streaming:
                        print(f"Stream worker error: {e}")
                    break
                    
        except Exception as e:
            print(f"❌ Stream worker fatal error: {e}")
        finally:
            print("🔄 EMG stream worker stopped")
    
    def stop_streaming(self):
        """Stop the EMG data streaming"""
        print("🛑 Stopping Delsys streaming...")
        
        self.streaming = False
        
        # Send stop command if command socket is available
        if self.command_socket:
            try:
                self.command_socket.sendall(b'TRIGGER STOP\r\n\r\n')
                print("Sent TRIGGER STOP command")
            except Exception as e:
                print(f"Error sending stop command: {e}")
        
        # Close sockets
        if self.stream_socket:
            try:
                self.stream_socket.close()
            except:
                pass
            self.stream_socket = None
            
        if self.command_socket:
            try:
                self.command_socket.close()
            except:
                pass
            self.command_socket = None
        
        # Wait for thread to finish
        if self.stream_thread and self.stream_thread.is_alive():
            self.stream_thread.join(timeout=2.0)
        
        print("✅ Delsys streaming stopped")