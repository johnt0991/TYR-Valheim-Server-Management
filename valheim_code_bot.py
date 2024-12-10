import subprocess
import time
import ctypes
import pyautogui
import pygetwindow as gw
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import threading
import requests
import psutil
from datetime import datetime, timedelta
import sys
import re


# Path to your .bat script
BAT_SCRIPT_PATH = "start_headless_server.bat"

# Discord webhook URL
WEBHOOK_URL = ""

# Variables to hold server information
session_name = ""
server_ip = ""
join_code = ""
server_running = False
process = None  # To hold the reference to the running process

# Reset scheduling variables
reset_enabled = False
reset_interval = 6  # Default reset interval in hours
reset_start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).time()
next_reset_time = None

def send_to_discord(message):
    """Send a message to Discord using a webhook."""
    if not WEBHOOK_URL:
        print("Webhook URL not set.")
        return
    payload = {"content": message}
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"Failed to send message: {response.status_code}, {response.text}")

def start_batch_script():
    """Runs the .bat script and captures the output."""
    global process, server_running
    process = subprocess.Popen(
        BAT_SCRIPT_PATH,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=True
    )
    server_running = True

    if reset_enabled and next_reset_time:
        print(f"The server has started. The next scheduled reset is at: {next_reset_time}")
        send_to_discord(f"The server has started. The next scheduled reset is at: {next_reset_time}")

    for line in process.stdout:
        print(line.strip())
        update_server_info(line.strip())
        update_text_widget(line.strip(), "all")
        
        if "WARNING" in line:
            update_text_widget(line.strip(), "warning")
        elif "ERROR" in line:
            update_text_widget(line.strip(), "error")

        # Dynamically capture session name using regex
        session_match = re.search(r'Session "(.*?)" registered with join code', line)
        if session_match:
            session_name = session_match.group(1)  # Dynamically extracted session name
            join_code = line.split(' ')[-1]
            message = f"Session Name: {session_name}.  Session join code: {join_code}"
            send_to_discord(message)
            update_text_widget(message, "join_code")

        if "This is the serverIP used to register the server" in line:
            server_ip = line.split(': ')[-1]
            update_server_info(line.strip())

    server_running = False
    update_server_info("Server has stopped.")

def update_server_info(line):
    """Update the Main tab with server information."""
    server_info = f"Session: {session_name}\nServer IP: {server_ip}\nJoin Code: {join_code}\n"
    text_area_main.delete(1.0, tk.END)
    text_area_main.insert(tk.END, server_info)

def update_text_widget(message, filter_type):
    """Update the corresponding text widget based on filter type."""
    # Always add the message to the All tab
    text_area_all.insert(tk.END, message + '\n')
    text_area_all.yview(tk.END)
    
    # Add the message to the specific tab if applicable
    widgets = {
        "warning": text_area_warning,
        "error": text_area_error,
        "join_code": text_area_join_code
    }
    if filter_type in widgets:
        widget = widgets[filter_type]
        widget.insert(tk.END, message + '\n')
        widget.yview(tk.END)

def stop_server():
    """Stop the server by sending CTRL+C (CTRL_C_EVENT) to the process."""
    try:
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if "valheim_server.exe" in proc.info['name']:
                pid = proc.info['pid']
                break
        if pid:
            handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
            ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, pid)
            time.sleep(5)
            pyautogui.write('y')
            pyautogui.press('enter')
            print(f"Sent CTRL+C (CTRL_C_EVENT) to process {pid}.")
        else:
            print("Process not found.")
    except Exception as e:
        print(f"Error stopping the server: {e}")

def enable_reset(reset_checkbox, reset_interval_entry, reset_start_time_dropdown):
    """Enable or disable the Reset Interval and Start Time fields based on the checkbox state."""
    global reset_enabled
    if reset_checkbox.instate(['selected']):
        reset_interval_entry.config(state='normal')
        reset_start_time_dropdown.config(state='normal')
        reset_enabled = True
        print("Reset scheduling enabled.")
    else:
        reset_interval_entry.config(state='disabled')
        reset_start_time_dropdown.config(state='disabled')
        reset_enabled = False
        print("Reset scheduling disabled.")

def schedule_resets():
    """Schedule server resets at the specified interval."""
    global reset_enabled, reset_interval, reset_start_time, next_reset_time
    while True:
        if reset_enabled:
            now = datetime.now()
            next_reset = datetime.combine(now.date(), reset_start_time)
            while next_reset <= now:
                next_reset += timedelta(hours=reset_interval)

            next_reset_time = next_reset
            time_to_wait = (next_reset - now).total_seconds()
            print(f"Next reset scheduled at: {next_reset_time}. Waiting {time_to_wait / 3600:.2f} hours.")

            # Notify on Discord 15 minutes before reset
            if time_to_wait > 900:
                threading.Timer(time_to_wait - 900, lambda: send_to_discord(
                    f"Server will restart at {next_reset.strftime('%Y-%m-%d %H:%M')}. 15 minutes remaining."
                )).start()

            time.sleep(time_to_wait)

            send_to_discord("Server is restarting.  Please wait until server is back up to reconnect")
            print("Server is restarting")
            stop_server()
            time.sleep(120)  # Wait 2 minutes
            threading.Thread(target=start_batch_script, daemon=True).start()
        else:
            # If reset scheduling is disabled, sleep briefly before checking again
            time.sleep(60)

def apply_reset_settings(interval_var, start_time_var):
    """Apply the reset settings and log the changes."""
    global reset_interval, reset_start_time, next_reset_time
    reset_interval = interval_var.get()
    reset_start_time = datetime.strptime(start_time_var.get(), "%H:%M").time()
    print(f"Reset settings applied. Interval: {reset_interval} hours, Start Time: {reset_start_time}.")

    now = datetime.now()
    next_reset = datetime.combine(now.date(), reset_start_time)
    while next_reset <= now:
        next_reset += timedelta(hours=reset_interval)

    next_reset_time = next_reset
    print(f"Next reset will occur at: {next_reset_time}")

def apply_webhook_settings(webhook_url_var):
    """Apply the webhook URL setting."""
    global WEBHOOK_URL
    WEBHOOK_URL = webhook_url_var.get()
    print(f"Webhook URL set to: {WEBHOOK_URL}")

def redirect_console_output():
    """Redirect all console output to the Console tab."""
    class ConsoleOutput:
        def __init__(self, widget):
            self.widget = widget

        def write(self, message):
            self.widget.insert(tk.END, message)
            self.widget.yview(tk.END)

        def flush(self):
            pass  # Required to make it compatible with print()

    sys.stdout = ConsoleOutput(text_area_console)
    sys.stderr = ConsoleOutput(text_area_console)
    
    
def clear_text_boxes():
    """Clears all scrolled text areas."""
    text_area_main.delete(1.0, tk.END)
    text_area_all.delete(1.0, tk.END)
    text_area_warning.delete(1.0, tk.END)
    text_area_error.delete(1.0, tk.END)
    text_area_join_code.delete(1.0, tk.END)
    text_area_console.delete(1.0, tk.END)
    

def create_gui():
    """Create the Tkinter GUI."""
    global text_area_main, text_area_all, text_area_warning, text_area_error, text_area_join_code, text_area_console

    window = tk.Tk()
    window.title("Output Monitor")
    notebook = ttk.Notebook(window)
    notebook.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    tab_main = tk.Frame(notebook)
    tab_all = tk.Frame(notebook)
    tab_warning = tk.Frame(notebook)
    tab_error = tk.Frame(notebook)
    tab_join_code = tk.Frame(notebook)
    tab_console = tk.Frame(notebook)
    tab_reset = tk.Frame(notebook)
    tab_webhook = tk.Frame(notebook)

    notebook.add(tab_main, text="Session Info")
    notebook.add(tab_all, text="All Messages")
    notebook.add(tab_warning, text="Warnings")
    notebook.add(tab_error, text="Errors")
    notebook.add(tab_join_code, text="Join Codes")
    notebook.add(tab_console, text="Console Printout")  
    notebook.add(tab_reset, text="Server Restart Settings")
    notebook.add(tab_webhook, text="Discord Webhook Settings")

    text_area_main = scrolledtext.ScrolledText(tab_main, width=80, height=10, wrap=tk.WORD)
    text_area_main.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_all = scrolledtext.ScrolledText(tab_all, width=80, height=20, wrap=tk.WORD)
    text_area_all.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_warning = scrolledtext.ScrolledText(tab_warning, width=80, height=20, wrap=tk.WORD)
    text_area_warning.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_error = scrolledtext.ScrolledText(tab_error, width=80, height=20, wrap=tk.WORD)
    text_area_error.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_join_code = scrolledtext.ScrolledText(tab_join_code, width=80, height=20, wrap=tk.WORD)
    text_area_join_code.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_console = scrolledtext.ScrolledText(tab_console, width=80, height=20, wrap=tk.WORD)  # Console Text Area
    text_area_console.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    reset_enabled_var = tk.BooleanVar()
    reset_interval_var = tk.IntVar(value=6)
    reset_start_time_var = tk.StringVar(value="00:00")

    reset_checkbox = ttk.Checkbutton(
        tab_reset, text="Enable Reset Scheduling",
        variable=reset_enabled_var,
        command=lambda: enable_reset(reset_checkbox, reset_interval_entry, reset_start_time_dropdown)
    )
    reset_checkbox.pack(pady=5)

    ttk.Label(tab_reset, text="Reset Interval (Hours):").pack()
    reset_interval_entry = ttk.Entry(tab_reset, textvariable=reset_interval_var, state='disabled')
    reset_interval_entry.pack(pady=5)

    ttk.Label(tab_reset, text="Reset Start Time (HH:MM):").pack()
    reset_start_time_dropdown = ttk.Entry(tab_reset, textvariable=reset_start_time_var, state='disabled')
    reset_start_time_dropdown.pack(pady=5)

    apply_button = tk.Button(tab_reset, text="Apply Settings", command=lambda: apply_reset_settings(reset_interval_var, reset_start_time_var))
    apply_button.pack(pady=10)

    ttk.Label(tab_webhook, text="Discord Webhook URL:").pack()
    webhook_url_var = tk.StringVar()
    webhook_entry = ttk.Entry(tab_webhook, textvariable=webhook_url_var, width=50)
    webhook_entry.pack(pady=5)
    webhook_apply_button = tk.Button(tab_webhook, text="Apply Webhook", command=lambda: apply_webhook_settings(webhook_url_var))
    webhook_apply_button.pack(pady=10)

    # Create a Frame for the buttons to line up horizontally
    button_frame = tk.Frame(window)
    button_frame.pack(pady=10)  # Pack the frame into the main window
    
    # Define buttons and pack them side-by-side into the button_frame
    stop_button = tk.Button(button_frame, text="Stop Server", command=stop_server)
    stop_button.pack(side=tk.LEFT, padx=5)
    
    clear_button = tk.Button(button_frame, text="Clear All", command=clear_text_boxes)
    clear_button.pack(side=tk.LEFT, padx=5)
    
    start_button = tk.Button(button_frame, text="Start Server", command=lambda: threading.Thread(target=start_batch_script, daemon=True).start())
    start_button.pack(side=tk.LEFT, padx=5)


    redirect_console_output()  # Redirect console output to the Console tab
    threading.Thread(target=schedule_resets, daemon=True).start()
    window.mainloop()

if __name__ == "__main__":
    create_gui()
