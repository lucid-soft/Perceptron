from pathlib import Path
import pygetwindow as gw
import logging

log = logging.getLogger(__name__)

ACTIVE_POLICY = "example_cv_only"  # Simply change this string to swap policies
DEBUG_VIEW = True  # Shows debug view window when True
SMOOTH_MOUSE = True # Whether to jump instantly or move smoothly to the target
USE_POSTMESSAGE = True # Simulate native hardware input through win32 POSTMESSAGE, uses Direct Input otherwise
CONFIDENCE_THRESHOLD = 0.02 # Using during training to temporarily allow for lower confidence to test model training
OPENCV_MATCH_THRESHOLD = 0.80 # Confidence level, but for OpenCV detections
WINDOW_NAME = "Runelite" # (Partial/Full) Name of the window you want to track, for finding window bounds
TARGET_FPS = 7 # How many times per second the bot will update


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent # Path to model
MODEL_NAME = "example-seg.pt"   # Can also be in .onnx format as well
MODEL_PATH = str(PROJECT_ROOT / "assets" / "models" / MODEL_NAME)
IMAGE_PATH = PROJECT_ROOT / "assets" / "images"
TRACKER_CONFIG = 'bytetrack.yaml' # Loaded automatically from source library, not contained in this project

def get_game_bounds():
    try:
        win = gw.getWindowsWithTitle(WINDOW_NAME)[0]
        return {
            "top": win.top + 180,       # Change the bounds to match your game window
            "left": win.left + 589,     # Debug mode can show you what's being recorded
            "width": 512,
            "height": 330
        }
    except IndexError:
        log.warning("Game client window not found! Falling back to defaults.")
        return {"top": 172, "left": 582, "width": 512, "height": 330}

CAPTURE_AREA = get_game_bounds()