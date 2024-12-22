import base64
from io import BytesIO
import pyautogui
import os
from simple_logger.logger import SimpleLogger

# _all_ = ['take_screenshot', 'press_key', 'hold_key', 'move_mouse', 'click_mouse']

LOGGER = SimpleLogger(__name__, log_file="game_interface.log")

def take_screenshot(filename="screenshot.png"):
    """Takes a screenshot of the screen and saves it to the specified filename."""
    screenshot = pyautogui.screenshot()

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
    content = {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": img_str}}
    
    return content

def press_key(key):
    """Simulates pressing and releasing a key."""
    pyautogui.press(key)
    print(f"Pressed key: {key}")

def hold_key(key, duration):
    """Simulates holding down a key for a specified duration (in seconds)."""
    pyautogui.keyDown(key)
    pyautogui.sleep(duration)
    pyautogui.keyUp(key)
    print(f"Held key '{key}' for {duration} seconds")

def move_mouse(x, y):
    """Moves the mouse cursor to the specified coordinates."""
    pyautogui.moveTo(x, y)
    print(f"Moved mouse to: {x}, {y}")

def click_mouse(button='left'):
    """Clicks the specified mouse button (left, right, middle)."""
    pyautogui.click(button=button)
    print(f"Clicked mouse button: {button}")
