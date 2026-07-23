import win32gui
import win32con
import win32api

def find_window_partial(title):
    data = {"title": title, "results": []}
    win32gui.EnumWindows(enum_window_callback, data)
    return data["results"][0][0] if data["results"] else None

def enum_window_callback(hwnd, matches):
    if not win32gui.IsWindowVisible(hwnd):
        return

    window_title = win32gui.GetWindowText(hwnd)

    if matches["title"].lower() in window_title.lower():
        matches["results"].append((hwnd, window_title))

def get_virtual_key_code(key):
    key = key.lower()

    key_map = {
        "enter": win32con.VK_RETURN,
        "return": win32con.VK_RETURN,
        "escape": win32con.VK_ESCAPE,
        "esc": win32con.VK_ESCAPE,
        "space": win32con.VK_SPACE,
        "tab": win32con.VK_TAB,
        "backspace": win32con.VK_BACK,
        "shift": win32con.VK_SHIFT,
        "ctrl": win32con.VK_CONTROL,
        "control": win32con.VK_CONTROL,
        "alt": win32con.VK_MENU,
        "left": win32con.VK_LEFT,
        "right": win32con.VK_RIGHT,
        "up": win32con.VK_UP,
        "down": win32con.VK_DOWN,
    }

    if key in key_map:
        return key_map[key]

    if len(key) == 1:
        return ord(key.upper())

    if key.startswith("f") and key[1:].isdigit():
        function_number = int(key[1:])

        if 1 <= function_number <= 24:
            return win32con.VK_F1 + function_number - 1

    return None

def make_key_lparam(vk_code, key_up=False):
    scan_code = win32api.MapVirtualKey(vk_code, 0)

    lparam = 1 | (scan_code << 16)

    if key_up:
        lparam |= (1 << 30)  # Previous key state
        lparam |= (1 << 31)  # Transition state

    return lparam