# EMG Data Streaming and Recording Application

This application provides a web-based interface for streaming and recording EMG data from a Delsys Trigno system. It has been restructured for better organization and modularity.

## Project Structure

```
GUI_EMG/
├── main.py                 # Main application entry point
├── config.py               # Configuration settings
├── utils.py                # Utility functions
├── delsys.py               # Delsys data handler
├── data_handler.py         # Data saving and processing
├── state_manager.py        # Application state management
├── delsys_simulator.py     # Delsys system simulator for testing
├── muscle_labels.yaml      # Muscle labels configuration
├── README.md               # This file
├── templates/
│   └── index.html          # Web interface
└── recordings/             # Default directory for saved recordings (created on first run)
```

## Modules Description

### main.py
The main Flask application that handles the web interface and routes. It initializes the application and manages the web server.

### config.py
Contains all configuration parameters for the application:
- Network settings (IP, ports)
- Data acquisition parameters (number of sensors, sampling rate)
- File and directory settings
- Signal processing parameters

### utils.py
Utility functions used across the application:
- Directory selection dialog
- Loading muscle labels from configuration file

### delsys.py
Handles connection and data streaming from the Delsys Trigno system:
- Socket communication
- Signal processing (filtering, rectification)
- Data streaming thread

### data_handler.py
Manages data saving and processing:
- Saving EMG recordings in MATLAB-compatible format
- Generating timestamps
- Saving metadata

### state_manager.py
Manages the application state:
- Streaming and recording state
- Data buffering for live visualization
- Recording worker thread

### delsys_simulator.py
A simulator for the Delsys system that generates realistic EMG signals for testing purposes.

### muscle_labels.yaml
Configuration file containing the muscle labels for each channel.

## Running the Application

1. Make sure you have all required dependencies installed:
   ```
   pip install flask numpy scipy pyyaml
   ```

2. Run the main application:
   ```
   python main.py
   ```

3. Open your web browser and navigate to `http://localhost:5000`

## Using the Simulator

For testing without actual hardware, you can run the Delsys simulator:
```
python delsys_simulator.py
```

Then run the main application as usual.

## Usage

1. Click "Start Streaming" to begin receiving data from the Delsys system
2. Click "Start Recording" to begin recording data to disk
3. Click "Stop Recording" to stop recording and save the data
4. Click "Stop Streaming" to stop streaming data

Recorded data is saved in the selected directory with the following structure:
```
recordings/
├── *.bin                  # Binary data files
├── metadata/
│   └── *.mat              # Metadata files
└── structs/
```