from pathlib import Path
import pygetwindow as gw
import logging

log = logging.getLogger(__name__)

ACTIVE_POLICY = "hill_giant"  # Simply change this string to swap bots
COMBAT_COOLDOWN_SECONDS = 6.0
DEBUG_VIEW = True  # Shows debug view window when True
SMOOTH_MOUSE = True # Whether to jump instantly or move smoothly to the target
USE_POSTMESSAGE = True # Simulate native hardware input through win32 POSTMESSAGE
CONFIDENCE_THRESHOLD = 0.02 # Using during training to temporarily allow for lower confidence to test model training
WINDOW_NAME = "Runelite"
TARGET_FPS = 7 # How many times per second the bot will update

# Path to model
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_NAME = "example-seg.pt"   # Can also be in .onnx format as well
MODEL_PATH = str(PROJECT_ROOT / "assets" / "models" / MODEL_NAME)
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
