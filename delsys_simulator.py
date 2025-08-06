# delsys_simulator.py - Realistic Delsys Trigno System Simulator with sub-millivolt signals

import socket
import struct
import threading
import time
import numpy as np
import signal
import sys
from datetime import datetime

class DelsysSimulator:
    """
    Simulates a Delsys Trigno system for testing EMG data collection applications.
    Mimics the exact protocol used by the real Delsys system with realistic EMG amplitude ranges.
    All signals are kept below 1mV (1e-3 V) to match real EMG recordings.
    """
    
    def __init__(self, host='127.0.0.1', num_sensors=4, sampling_rate=2000.0):
        self.host = host
        self.num_sensors = num_sensors
        self.sampling_rate = sampling_rate
        
        # Ports matching your application
        self.COMMAND_PORT = 50040
        self.STREAM_PORT = 50041
        
        # Server sockets
        self.command_server = None
        self.stream_server = None
        
        # Client connections
        self.command_conn = None
        self.stream_conn = None
        
        # Control flags
        self.running = False
        self.streaming = False
        self.trigger_active = False
        
        # Threads
        self.command_thread = None
        self.stream_thread = None
        self.data_thread = None
        
        # EMG simulation parameters
        self.time_offset = 0.0
        self.muscle_profiles = self._create_muscle_profiles()
        
        print(f"🎭 Realistic EMG Simulator initialized (sub-millivolt signals)")
        print(f"   Host: {self.host}")
        print(f"   Command Port: {self.COMMAND_PORT}")
        print(f"   Stream Port: {self.STREAM_PORT}")
        print(f"   Sensors: {self.num_sensors}")
        print(f"   Sampling Rate: {self.sampling_rate} Hz")
        print(f"   Signal Range: 10-800 µV (0.00001 - 0.0008 V)")
    
    def _create_muscle_profiles(self):
        """Create realistic EMG signal profiles with sub-millivolt amplitudes"""
        muscle_names = [
            'L-MASS', 'L-MYLO', 'R-MASS', 'R-MYLO'
        ]
        
        profiles = {}
        for i, name in enumerate(muscle_names[:self.num_sensors]):
            if 'NC' in name:
                # No connection - just baseline noise (5-15 µV)
                profiles[i] = {
                    'name': name,
                    'base_amplitude': np.random.uniform(5e-6, 15e-6),
                    'frequency': 0.0,
                    'burst_frequency': 0.0,
                    'noise_level': np.random.uniform(3e-6, 8e-6),
                    'max_activation': 0.0
                }
            else:
                # Active muscle with realistic EMG parameters
                # Typical EMG ranges: 10-800 µV for surface EMG
                base_activation = np.random.uniform(20e-6, 80e-6)
                max_activation = np.random.uniform(200e-6, 800e-6)
                
                profiles[i] = {
                    'name': name,
                    'base_amplitude': base_activation,
                    'frequency': np.random.uniform(80, 120),
                    'burst_frequency': np.random.uniform(0.3, 1.5),
                    'noise_level': np.random.uniform(8e-6, 20e-6),
                    'max_activation': max_activation,
                    'contraction_threshold': np.random.uniform(0.998, 0.9995),
                    'fatigue_factor': np.random.uniform(0.95, 0.99)
                }
                
                print(f"   📊 {name}: Rest={base_activation*1e6:.1f}µV, Max={max_activation*1e6:.1f}µV")
        
        return profiles
    
    def _generate_emg_sample(self, channel_id, timestamp):
        """Generate a realistic EMG sample with sub-millivolt amplitudes"""
        if channel_id not in self.muscle_profiles:
            # Fallback noise for undefined channels
            return np.random.normal(0, 10e-6)
        
        profile = self.muscle_profiles[channel_id]
        
        # Base electrical noise (always present)
        base_noise = np.random.normal(0, profile['noise_level'])
        
        if profile['frequency'] == 0.0:
            return base_noise
        
        # Simulate realistic EMG signal characteristics
        
        # Main EMG frequency content (motor unit firing patterns)
        # Multiple frequency components to simulate motor unit recruitment
        main_freq = profile['frequency']
        emg_signal = (
            np.sin(2 * np.pi * main_freq * timestamp) +
            0.6 * np.sin(2 * np.pi * main_freq * 1.3 * timestamp) +
            0.4 * np.sin(2 * np.pi * main_freq * 0.7 * timestamp) +
            0.3 * np.sin(2 * np.pi * main_freq * 2.1 * timestamp) +
            0.2 * np.random.random()
        )
        
        # Add DC offset to simulate real-world conditions
        dc_offset = np.random.uniform(-50e-6, 50e-6)
        
        # Rectify and apply realistic amplitude modulation
        emg_signal = np.abs(emg_signal)
        
        # Muscle activation level (varies over time)
        # Base activation level
        activation_level = profile['base_amplitude']
        
        # Add slow muscle activation variations (breathing, posture changes)
        slow_modulation = 1.0 + 0.3 * np.sin(2 * np.pi * 0.1 * timestamp)
        slow_modulation += 0.2 * np.sin(2 * np.pi * 0.05 * timestamp)
        
        # Add muscle burst patterns (voluntary or involuntary contractions)
        burst_modulation = 1.0 + 0.4 * np.sin(2 * np.pi * profile['burst_frequency'] * timestamp)
        
        # Occasional strong contractions (very rare)
        contraction_multiplier = 1.0
        if np.random.random() > profile['contraction_threshold']:
            # Strong contraction (reaches max activation)
            contraction_strength = np.random.uniform(0.5, 1.0)
            contraction_multiplier = 1.0 + contraction_strength * (
                profile['max_activation'] / profile['base_amplitude'] - 1.0
            )
            print(f"💪 {profile['name']}: Strong contraction! "
                  f"{activation_level * contraction_multiplier * 1e6:.0f}µV")
        
        # Apply fatigue factor (slight decrease over time)
        fatigue_factor = profile['fatigue_factor'] ** (timestamp / 60.0)
        
        # Combine all components
        final_amplitude = (
            activation_level * 
            slow_modulation * 
            burst_modulation * 
            contraction_multiplier * 
            fatigue_factor
        )
        
        # Apply to EMG signal and add noise and DC offset
        final_signal = emg_signal * final_amplitude + base_noise + dc_offset
        
        # Ensure signal stays within realistic bounds (never above 1mV)
        final_signal = np.clip(final_signal, -1e-3, 1e-3)
        
        return final_signal
    
    def start(self):
        """Start the simulator servers"""
        try:
            print("🚀 Starting Realistic EMG Simulator...")
            
            # Create server sockets
            self.command_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.command_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.command_server.bind((self.host, self.COMMAND_PORT))
            self.command_server.listen(1)
            
            self.stream_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.stream_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.stream_server.bind((self.host, self.STREAM_PORT))
            self.stream_server.listen(1)
            
            self.running = True
            
            # Start server threads
            self.command_thread = threading.Thread(target=self._command_server_worker, daemon=True)
            self.stream_thread = threading.Thread(target=self._stream_server_worker, daemon=True)
            
            self.command_thread.start()
            self.stream_thread.start()
            
            print(f"✅ Command server listening on {self.host}:{self.COMMAND_PORT}")
            print(f"✅ Stream server listening on {self.host}:{self.STREAM_PORT}")
            print("📡 Waiting for client connections...")
            
            return True
            
        except Exception as e:
            print(f"❌ Error starting simulator: {e}")
            self.stop()
            return False
    
    def _command_server_worker(self):
        """Handle command connections and protocol"""
        print("🎮 Command server worker started")
        
        while self.running:
            try:
                # Accept connection
                print("⏳ Waiting for command connection...")
                self.command_conn, addr = self.command_server.accept()
                print(f"🔗 Command client connected from {addr}")
                
                # Handle commands from this client
                while self.running and self.command_conn:
                    try:
                        # Receive command with timeout
                        self.command_conn.settimeout(1.0)
                        data = self.command_conn.recv(1024)
                        
                        if not data:
                            print("🔌 Command client disconnected")
                            break
                        
                        command = data.decode('utf-8', errors='ignore').strip()
                        print(f"📨 Received command: '{command}'")
                        
                        # Process commands
                        if command == 'START':
                            print("▶️  Processing START command")
                            self.streaming = True
                            # Send acknowledgment
                            try:
                                self.command_conn.send(b'OK\r\n')
                            except:
                                pass
                        
                        elif command.startswith('TRIGGER START'):
                            print("🎯 Processing TRIGGER START command")
                            self.trigger_active = True
                            if not self.data_thread or not self.data_thread.is_alive():
                                self.data_thread = threading.Thread(target=self._data_generator_worker, daemon=True)
                                self.data_thread.start()
                            # Send acknowledgment
                            try:
                                self.command_conn.send(b'OK\r\n')
                            except:
                                pass
                        
                        elif command.startswith('TRIGGER STOP'):
                            print("🛑 Processing TRIGGER STOP command")
                            self.trigger_active = False
                            # Send acknowledgment
                            try:
                                self.command_conn.send(b'OK\r\n')
                            except:
                                pass
                        
                        elif command == 'STOP':
                            print("⏹️  Processing STOP command")
                            self.streaming = False
                            self.trigger_active = False
                            # Send acknowledgment
                            try:
                                self.command_conn.send(b'OK\r\n')
                            except:
                                pass
                        
                        else:
                            print(f"❓ Unknown command: '{command}'")
                            # Send acknowledgment anyway
                            try:
                                self.command_conn.send(b'OK\r\n')
                            except:
                                pass
                    
                    except socket.timeout:
                        continue
                    except Exception as e:
                        print(f"❌ Error in command handler: {e}")
                        break
            
            except Exception as e:
                if self.running:
                    print(f"❌ Error in command server: {e}")
                    time.sleep(1)
        
        print("🎮 Command server worker stopped")
    
    def _stream_server_worker(self):
        """Handle stream connections"""
        print("📡 Stream server worker started")
        
        while self.running:
            try:
                # Accept connection
                print("⏳ Waiting for stream connection...")
                self.stream_conn, addr = self.stream_server.accept()
                print(f"🔗 Stream client connected from {addr}")
                
                # Keep connection alive while running
                while self.running and self.stream_conn:
                    try:
                        # Just keep the connection alive
                        # The actual data sending is handled by the data generator
                        time.sleep(1.0)
                        
                        # Check if client is still connected
                        self.stream_conn.settimeout(0.1)
                        try:
                            ready = self.stream_conn.recv(1, socket.MSG_PEEK)
                            if not ready:
                                print("🔌 Stream client disconnected")
                                break
                        except socket.timeout:
                            # This is expected - client is just listening
                            pass
                        except:
                            print("🔌 Stream client disconnected")
                            break
                            
                    except Exception as e:
                        print(f"❌ Error maintaining stream connection: {e}")
                        break
            
            except Exception as e:
                if self.running:
                    print(f"❌ Error in stream server: {e}")
                    time.sleep(1)
        
        print("📡 Stream server worker stopped")
    
    def _data_generator_worker(self):
        """Generate and send EMG data when triggered"""
        print("🎲 Data generator worker started")
        
        sample_interval = 1.0 / self.sampling_rate
        next_sample_time = time.time()
        sample_count = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Check if we should send data
                if (self.streaming and self.trigger_active and 
                    self.stream_conn and current_time >= next_sample_time):
                    
                    # Generate EMG data for all channels (pad to 16 for protocol compatibility)
                    timestamp = self.time_offset + sample_count * sample_interval
                    emg_samples = []
                    
                    # Generate data for active channels
                    for channel_id in range(self.num_sensors):
                        sample = self._generate_emg_sample(channel_id, timestamp)
                        emg_samples.append(float(sample))
                    
                    # Pad remaining channels with realistic noise to maintain 16-channel protocol
                    while len(emg_samples) < 16:
                        # Add small noise for unused channels
                        noise_sample = np.random.normal(0, 5e-6)
                        emg_samples.append(float(noise_sample))
                    
                    # Pack as 16 little-endian floats (64 bytes total)
                    try:
                        packed_data = struct.pack('<16f', *emg_samples)
                        self.stream_conn.send(packed_data)
                        
                        sample_count += 1
                        next_sample_time += sample_interval
                        
                        # Debug output (less frequent) - show in microvolts for readability
                        if sample_count % 4000 == 0:
                            print(f"📊 Sent {sample_count} samples | " +
                                  " | ".join([f"Ch{i}: {emg_samples[i]*1e6:+4.0f}µV" 
                                            for i in range(min(4, self.num_sensors))]))
                        
                    except Exception as e:
                        print(f"❌ Error sending data: {e}")
                        # Connection probably lost
                        break
                
                else:
                    # Sleep briefly to avoid busy waiting
                    time.sleep(0.0001)
                
            except Exception as e:
                print(f"❌ Error in data generator: {e}")
                break
        
        print("🎲 Data generator worker stopped")
    
    def stop(self):
        """Stop the simulator"""
        print("🛑 Stopping Realistic EMG Simulator...")
        
        self.running = False
        self.streaming = False
        self.trigger_active = False
        
        # Close client connections
        if self.command_conn:
            try:
                self.command_conn.close()
            except:
                pass
            self.command_conn = None
        
        if self.stream_conn:
            try:
                self.stream_conn.close()
            except:
                pass
            self.stream_conn = None
        
        # Close server sockets
        if self.command_server:
            try:
                self.command_server.close()
            except:
                pass
            self.command_server = None
        
        if self.stream_server:
            try:
                self.stream_server.close()
            except:
                pass
            self.stream_server = None
        
        # Wait for threads to finish
        for thread in [self.command_thread, self.stream_thread, self.data_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=2.0)
        
        print("✅ Realistic EMG Simulator stopped")
    
    def status(self):
        """Get current simulator status"""
        return {
            'running': self.running,
            'streaming': self.streaming,
            'trigger_active': self.trigger_active,
            'command_connected': self.command_conn is not None,
            'stream_connected': self.stream_conn is not None,
            'sampling_rate': self.sampling_rate,
            'num_sensors': self.num_sensors,
            'signal_range': '10-800 µV (sub-millivolt)'
        }

def main():
    """Main function to run the realistic EMG simulator"""
    simulator = None
    
    def signal_handler(sig, frame):
        print("\n🛑 Received shutdown signal...")
        if simulator:
            simulator.stop()
        sys.exit(0)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Create and start simulator
        simulator = DelsysSimulator(
            host='127.0.0.1',
            num_sensors=4,
            sampling_rate=2000.0
        )
        
        if simulator.start():
            print("✅ Realistic EMG Simulator is running!")
            print("🎯 Connect your EMG application to:")
            print(f"   Command Port: 127.0.0.1:{simulator.COMMAND_PORT}")
            print(f"   Stream Port: 127.0.0.1:{simulator.STREAM_PORT}")
            print("📊 Generating realistic EMG signals (10-800 µV range)")
            print("⏹️  Press Ctrl+C to stop")
            
            # Keep running until interrupted
            while simulator.running:
                time.sleep(1)
        else:
            print("❌ Failed to start simulator")
            return 1
    
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return 1
    
    finally:
        if simulator:
            simulator.stop()
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)