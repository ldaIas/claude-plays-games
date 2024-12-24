import base64
from io import BytesIO
import pyautogui
import pydirectinput
from PIL import ImageGrab
import os
import sys
from functools import partial

# Uncomment for testing in main script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simple_logger.logger import SimpleLogger

# _all_ = ['take_screenshot', 'press_key', 'hold_key', 'move_mouse', 'click_mouse']

LOGGER = SimpleLogger(__name__, log_file="game_interface.log")

def take_screenshot(filename="screenshot.png"):
    """Takes a screenshot of the screen and saves it to the specified filename."""
    screenshot = ImageGrab.grab(all_screens=False)

    # Create output directory if it doesn't exist
    if not os.path.exists("output"):
        os.makedirs("output")
    screenshot.save("output/"+filename)
    LOGGER.debug(f"Screenshot saved as {filename}")

    # Convert PIL Image to base64 string
    buffered = BytesIO()
    screenshot.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()

    # Return the image in a content[] block for returning to Claude
    content = {
        "type": "tool_result",
        "content": [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_str}}]
    }
    
    return content

def validate_key(key):
    """
    Validates that the key is a valid key. 
    Returns a content response if key is invalid for sending back to claude.
    """

    valid_keys = pyautogui.KEYBOARD_KEYS
    valid_mouse_buttons = ['lmb', 'rmb', 'mmb']
    
    if key not in valid_keys and key not in valid_mouse_buttons:
        LOGGER.warning(f"Invalid key input '{key}'.")

        return { "type": "tool_result",
                 "content": [{
                    "type": "text",
                    "text": f"Invalid key '{key}'. Must be a valid keyboard key or mouse button."
            }]
        }
    return None

def press_key(key):
    """Simulates pressing and releasing a key."""
    key = str.lower(key)
    validation_result = validate_key(key)
    if validation_result is not None:
        return validation_result

    if key == "lmb":
        pydirectinput.click()
    elif key == "rmb":
        pydirectinput.rightClick()
    elif key == "mmb":
        pydirectinput.middleClick()
    else:    
        pydirectinput.press(key)
    LOGGER.debug(f"Pressed key '{key}'")

    content = {
        "type": "tool_result",
        "content": f"Pressed key '{key}'"
    }
    return content

def hold_key(key, duration=1):
    """Simulates holding down a key for a specified duration (in seconds)."""
    key = str.lower(key)
    validation_result = validate_key(key)
    if validation_result is not None:
        return validation_result
    
    if key in ["lmb", "rmb", "mmb"]:
        # Handle mouse buttons as before
        button = 'left' if key == "lmb" else 'right' if key == "rmb" else 'middle'
        pydirectinput.mouseDown(button=button, duration=duration)   
    else:
        pydirectinput.keyDown(key)
        pyautogui.sleep(duration)
        pydirectinput.keyUp(key)

    fn_result = f"Held key '{key}' for {duration} seconds"
    LOGGER.debug(fn_result)

    content = {
        "type": "tool_result",
        "content": fn_result
    }
    return content

def move_mouse(x, y, duration=0.1):
    """Moves the mouse cursor to the specified coordinates."""
    pydirectinput.moveRel(x, y, duration=duration, relative=True)
    LOGGER.debug(f"Moved mouse to: {x}, {y}")

    return {
        "type": "tool_result",
        "content": f"Moved mouse to: {x}, {y}"
    }


# Main script for testing inputs
# Uncomment the line above the logger import to run
if __name__ == "__main__":
    # Example usage
    # take_screenshot()
    # press_key('a')
    # hold_key('a', 2)
    # move_mouse(100, 100)
    # click_mouse('left')
    # click_mouse('right')
    # click_mouse('middle')
    # click_mouse('invalid_button')
    pyautogui.sleep(1.5)
    print(move_mouse(960, 0))