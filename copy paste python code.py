import os
import time
import threading
import win32clipboard
import win32con
import tkinter as tk
from tkinter import messagebox
import keyboard
import pywintypes

# Global variables
clipboard_stack = []
listener_active = False
stop_copy_listener = threading.Event()
MAX_STACK_SIZE = 20  # Added maximum stack size

def get_clipboard_text(delay_after_copy=0.15, open_attempts=5, data_attempts=3, open_retry_delay=0.05, data_retry_delay=0.05):
    """
    Retrieves text from the clipboard with error handling and retries.

    Args:
        delay_after_copy (float): Delay after copy event before accessing clipboard.
        open_attempts (int): Number of attempts to open the clipboard.
        data_attempts (int): Number of attempts to get data from the clipboard.
        open_retry_delay (float): Delay between retrying to open the clipboard.
        data_retry_delay (float): Delay between retrying to get data from the clipboard.

    Returns:
        str: The text from the clipboard, or None on failure.
    """
    time.sleep(delay_after_copy)

    for attempt_open in range(open_attempts):
        try:
            win32clipboard.OpenClipboard()
            try:
                for attempt_data in range(data_attempts):
                    if win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                        text = win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)
                        return text
                    elif attempt_data < data_attempts - 1:
                        time.sleep(data_retry_delay)
                    else:
                        return None
                return None
            finally:
                win32clipboard.CloseClipboard()

        except pywintypes.error as e:
            error_code = e.winerror if hasattr(e, 'winerror') else 'N/A'
            print(f"Clipboard pywintypes error (Code: {error_code}): {e}. Open attempt {attempt_open + 1}/{open_attempts}.")
            if attempt_open < open_attempts - 1:
                time.sleep(open_retry_delay)
            else:
                print("Max open attempts reached for clipboard.")
                return None
        except Exception as e:
            print(f"Unexpected clipboard error: {e}. Open attempt {attempt_open + 1}/{open_attempts}.")
            if attempt_open < open_attempts - 1:
                time.sleep(open_retry_delay)
            else:
                print("Max open attempts reached due to unexpected error.")
                return None
    return None

def copy_event_listener():
    """
    Listens for Ctrl+C to capture clipboard text and add it to the stack.
    """
    while True:
        if listener_active:
            stop_copy_listener.clear()
            try:
                keyboard.wait('ctrl+c')
                if stop_copy_listener.is_set():
                    continue
                time.sleep(0.1)
                data = get_clipboard_text()
                if data and data.strip():
                    clipboard_stack.append(data)
                    if len(clipboard_stack) > MAX_STACK_SIZE:
                        clipboard_stack.pop(0)
            except keyboard.Listener.HotKeyRecorder.StopException:
                break
        else:
            time.sleep(0.1)
            stop_copy_listener.set()

def paste_and_reset():
    """
    Pastes the combined text from the stack to the clipboard and clears the stack.
    """
    if clipboard_stack:
        combined_text = "\n".join(clipboard_stack)
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(combined_text, win32con.CF_UNICODETEXT)
            win32clipboard.CloseClipboard()
            clipboard_stack.clear()
        except Exception as e:
            print(f"Paste error: {e}")
            messagebox.showerror("Paste Error", f"Could not paste to clipboard: {e}")

def monitor_paste_hotkey():
    """
    Monitors Ctrl+V to trigger pasting the combined text.
    """
    while True:
        keyboard.wait('ctrl+v')
        if clipboard_stack:
            paste_and_reset()

def toggle_listener():
    """
    Toggles the clipboard listener on and off.  Also clears the stack when turning on.
    """
    global listener_active
    global stop_copy_listener
    listener_active = not listener_active

    if listener_active:
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"Error clearing clipboard: {e}")
        clipboard_stack.clear()
        print("Listener ON. System clipboard and stack cleared.")
        stop_copy_listener.clear()
    else:
        print("Listener OFF.")
        stop_copy_listener.set()
        time.sleep(0.1)

    toggle_button.config(text="Turn OFF" if listener_active else "Turn ON")

# --- GUI Setup ---
root = tk.Tk()
root.title("Smart Multi Stack Copy")
root.geometry("200x100")  # Reduced size for minimal UI
root.resizable(False, False)  # Make the window fixed size

# Remove the status label
# status_label = tk.Label(root, text="Status: OFF ❌", fg="red", font=("Arial", 12))
# status_label.pack(pady=5)

toggle_button = tk.Button(root, text="Turn ON", command=toggle_listener, width=15, height=2)
toggle_button.pack(pady=20)

# Remove the display box
# display_box = scrolledtext.ScrolledText(root, width=70, height=15, state='disabled')
# display_box.pack(padx=10, pady=10)

# Start background threads
threading.Thread(target=copy_event_listener, daemon=True).start()
threading.Thread(target=monitor_paste_hotkey, daemon=True).start()

root.mainloop()
