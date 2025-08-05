# emg_data_saver.py
"""
Dedicated module for saving EMG data in the correct format for MATLAB compatibility.
This module ensures data is saved as (samples, channels+1) matrix format.
"""
import numpy as np
import scipy.io
import os
import datetime

def save_emg_recording(save_directory, recording_data_buffer, start_time, sampling_rate, 
                      muscle_labels, recording_session_start_time, trial_counter):
    """
    Save EMG recording data in MATLAB-compatible format.
    
    Args:
        save_directory: Base directory for saving files
        recording_data_buffer: List where [0] is timestamps, [1:] are channel data
        start_time: Recording start timestamp
        sampling_rate: Sampling rate in Hz
        muscle_labels: List of muscle label strings
        recording_session_start_time: Session start datetime
        trial_counter: Current trial number
    
    Returns:
        tuple: (success, message, min_samples)
    """
    try:
        # Create subdirectories
        metadata_directory = os.path.join(save_directory, "metadata")
        structs_directory = os.path.join(save_directory, "structs")
        os.makedirs(metadata_directory, exist_ok=True)
        os.makedirs(structs_directory, exist_ok=True)
        
        # Analyze data and find minimum sample count
        num_sensors = len(recording_data_buffer) - 1
        sample_counts = [len(recording_data_buffer[i]) for i in range(1, num_sensors + 1)]
        
        if not sample_counts or all(count == 0 for count in sample_counts):
            return False, "No data was captured.", 0
            
        min_samples = min(sample_counts)
        print(f"Minimum samples across channels: {min_samples}")
        
        if min_samples == 0:
            return False, "No data was captured (after trimming).", 0
        
        # Generate timestamps
        timestamps = generate_timestamps(min_samples, start_time, sampling_rate)
        
        # Create data matrix in MATLAB-compatible format: (samples, channels+1)
        # First column: timestamps, subsequent columns: channel data
        data_matrix = np.zeros((min_samples, num_sensors + 1), dtype=np.float64)
        data_matrix[:, 0] = timestamps
        
        # Fill in channel data, ensuring all channels have the same length
        for i in range(1, num_sensors + 1):
            buffer_data = recording_data_buffer[i]
            
            if len(buffer_data) > min_samples:
                # Trim excess data
                channel_data = np.array(buffer_data[:min_samples], dtype=np.float64)
            elif len(buffer_data) < min_samples:
                # Pad with zeros if needed
                padded_data = buffer_data + [0.0] * (min_samples - len(buffer_data))
                channel_data = np.array(padded_data, dtype=np.float64)
                print(f"Warning: Padding channel {i-1} data.")
            else:
                channel_data = np.array(buffer_data, dtype=np.float64)
            
            data_matrix[:, i] = channel_data
        
        # Generate filenames with structured naming
        timestamp_str = recording_session_start_time.strftime("%Y%m%d_%H%M%S")
        trial_str = f"{trial_counter:04d}"
        filename_base = f"{timestamp_str}_Trl{trial_str}"
        
        bin_filename = os.path.join(save_directory, f"{filename_base}.bin")
        meta_filename = os.path.join(metadata_directory, f"{timestamp_str}_METADATATrl{trial_str}.mat")
        
        # Save binary data in the correct format
        data_matrix.tofile(bin_filename)
        print(f"Binary data saved to {bin_filename}")
        print(f"Data shape: {data_matrix.shape} (samples, channels+1)")
        
        # Verify data format
        print(f"First few timestamps: {timestamps[:5]}")
        print(f"Time range: {timestamps[0]:.6f} to {timestamps[-1]:.6f} seconds")
        print(f"Time step: {timestamps[1] - timestamps[0]:.6f} seconds")
        
        # Save metadata
        success_meta = save_metadata(meta_filename, num_sensors, sampling_rate, 
                                   muscle_labels, recording_session_start_time, trial_counter)
        if not success_meta:
            print("Warning: Could not save metadata file")
        
        return True, f"Recording saved successfully ({min_samples} samples).", min_samples
        
    except Exception as e:
        return False, f"Error saving recording: {str(e)}", 0

def generate_timestamps(num_samples, start_time, sampling_rate):
    """Generate relative timestamps starting from 0."""
    # Always generate relative timestamps starting from 0
    # This matches the format expected by MATLAB and used in debug_data_saver.py
    return np.arange(num_samples, dtype=np.float64) / sampling_rate

def save_metadata(meta_filename, num_sensors, sampling_rate, muscle_labels, 
                 recording_session_start_time, trial_counter):
    """Save metadata file in MATLAB format."""
    try:
        meta_data = {}
        meta_data['emg_ch_number'] = np.array(range(1, num_sensors + 1))
        meta_data['fs'] = float(sampling_rate)
        meta_data['total_analog_in_ch'] = float(num_sensors)
        meta_data['musc_labels'] = np.array(muscle_labels, dtype=object)
        meta_data['session_date'] = recording_session_start_time.strftime("%Y-%m-%d")
        meta_data['session_time'] = recording_session_start_time.strftime("%H:%M:%S")
        meta_data['trial_number'] = int(trial_counter)
        
        scipy.io.savemat(meta_filename, {'meta_data': meta_data}, format='5')
        print(f"Metadata saved to {meta_filename}")
        return True
        
    except Exception as e:
        print(f"Error saving metadata: {e}")
        return False

def validate_data_format(data_matrix, expected_samples, expected_sensors):
    """Validate that the data matrix has the correct format."""
    expected_shape = (expected_samples, expected_sensors + 1)
    if data_matrix.shape != expected_shape:
        raise ValueError(f"Data matrix shape {data_matrix.shape} does not match expected {expected_shape}")
    
    # Check that timestamps are reasonable (monotonically increasing)
    timestamps = data_matrix[:, 0]
    if not np.all(np.diff(timestamps) > 0):
        print("Warning: Timestamps are not monotonically increasing")
    
    return True