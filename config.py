"""Configuration module for EMG application."""

import os

# Network configuration
HOST_IP = '127.0.0.1'
EMG_COMMAND_PORT = 50040
EMG_STREAM_PORT = 50041

# Data acquisition configuration
NUM_SENSORS = 4
ACTIVE_CHANNELS = 4
SAMPLING_RATE = 2000.0

# File and directory configuration
DEFAULT_SAVE_DIRECTORY = "./recordings"
MUSCLE_LABELS_FILE = "muscle_labels.yaml"

# Signal processing configuration
NOTCH_FREQ = 60.0
NOTCH_Q = 30.0
HP_FREQ = 0.5