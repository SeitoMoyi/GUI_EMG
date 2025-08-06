"""Utility functions for the EMG application."""

import os
import tkinter as tk
from tkinter import filedialog
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


def load_muscle_labels(config_file="muscle_labels.yaml"):
    """Load muscle labels from YAML configuration file."""
    try:
        yaml_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), config_file)
        print(f"🔍 Looking for muscle labels file at: {yaml_path}")
        with open(yaml_path, 'r') as f:
            config = yaml.safe_load(f)
            muscle_labels = config.get('muscle_labels', ['L-TIBI', 'L-GAST', 'L-RECT', 'R-TIBI'])
            print(f"✅ Loaded muscle labels: {muscle_labels}")
            return muscle_labels
    except FileNotFoundError:
        print("⚠️  muscle_labels.yaml not found. Using default labels.")
        return ['L-TIBI', 'L-GAST', 'L-RECT', 'R-TIBI']
    except Exception as e:
        print(f"❌ Error loading muscle labels: {e}. Using default labels.")
        return ['L-TIBI', 'L-GAST', 'L-RECT', 'R-TIBI']