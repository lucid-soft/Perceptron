import logging
import keyboard
from src.perceptron.action import ActionLayer
from src.perceptron.logging_config import configure_logging
from src.perceptron.perception import PerceptionLayer
from src.perceptron.config import CAPTURE_AREA, ACTIVE_POLICY, DEBUG_VIEW
from src.perceptron.policy import POLICIES

log = logging.getLogger(__name__)

def main():
    configure_logging(debug=DEBUG_VIEW) # Can just set this to True if you want debug logging without the debug window
    log.info("Booting up Perceptron...")

    action_layer = ActionLayer(capture_area=CAPTURE_AREA)

    # Select active policy strategy
    policy_class = POLICIES.get(ACTIVE_POLICY)
    if not policy_class:
        raise ValueError(f"Policy '{ACTIVE_POLICY}' not found in registry!")

    policy = policy_class(action_layer=action_layer, capture_area=CAPTURE_AREA)

    # Inject policy strategy directly into the vision pipeline
    perception_layer = PerceptionLayer(policy_layer=policy)

    # Global hotkey registration
    keyboard.add_hotkey('esc', perception_layer.stop)
    keyboard.add_hotkey('insert', perception_layer.pause)
    log.info(f"Active Script: {policy.__class__.__name__}")
    log.info("Tracking active. Press 'Escape' to safely abort.")

    try:
        perception_layer.start_loop()
    except Exception:
        log.exception("Fatal application error! (You most likely forgot to add the pre-trained model.)")
    finally:
        keyboard.unhook_all()

    keyboard.unhook_all()
    log.info("Perceptron shutdown successful. Goodbye.")

if __name__ == "__main__":
    main()