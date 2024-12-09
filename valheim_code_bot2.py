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

# Path to your .bat script
BAT_SCRIPT_PATH = "start_headless_server.bat"

# Discord webhook URL
WEBHOOK_URL = "https://discord.com/api/webhooks/1314664724360597655/g_93Lml_J1_t_Q9PDJrjUtj9e4xHGuJWl4G9qV5VCa43iU_BXdqng6zbMA3yGWjI_gm5"

# Variables to hold server information
session_name = "Nufu Gaming"
server_ip = ""
join_code = ""
server_running = False
process = None  # To hold the reference to the running process

# Reset scheduling variables
reset_enabled = False
reset_interval = 6  # Default reset interval in hours
reset_start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).time()


def send_to_discord(message):
    """Send a message to Discord using a webhook."""
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
    for line in process.stdout:
        print(line.strip())
        update_server_info(line.strip())
        update_text_widget(line.strip(), "all")
        if "WARNING" in line:
            update_text_widget(line.strip(), "warning")
        elif "ERROR" in line:
            update_text_widget(line.strip(), "error")
        if "Session \"Nufu Gaming\" registered with join code" in line:
            join_code = line.split(' ')[-1]
            message = f"Session Name: Nufu Gaming.  Session join code: {join_code}"
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
    widgets = {
        "all": text_area_all,
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
    if reset_checkbox.instate(['selected']):
        reset_interval_entry.config(state='normal')
        reset_start_time_dropdown.config(state='normal')
    else:
        reset_interval_entry.config(state='disabled')
        reset_start_time_dropdown.config(state='disabled')


from datetime import datetime, timedelta

def schedule_resets():
    """Handles the scheduling of server resets based on user settings."""
    global reset_enabled, reset_interval, reset_start_time  # Ensure these are accessible

    while True:
        if reset_enabled:
            now = datetime.now()
            next_reset = datetime.combine(now.date(), reset_start_time)

            # Calculate the next reset time
            while next_reset < now:
                next_reset += timedelta(hours=reset_interval)

            wait_time = (next_reset - now).total_seconds()
            hours, remainder = divmod(wait_time, 3600)
            minutes, _ = divmod(remainder, 60)

            # Print the next reset time immediately
            message = f"Next reset scheduled in: {int(hours)} hours and {int(minutes)} minutes at {next_reset.strftime('%I:%M %p')}."
            print(message)
            update_text_widget(message, "all")

            # Check for when 15 minutes are left
            notify_15_min_time = wait_time - 900  # 15 minutes in seconds
            
            if notify_15_min_time > 0:
                # Wait until 15 minutes before the reset
                print("Waiting for 15 minutes notification...")
                time.sleep(notify_15_min_time)  # Sleep until we are at 15 minutes left
                discord_message = f"⚠️ Scheduled server reset in 15 minutes at {next_reset.strftime('%I:%M %p')}. Please save your progress!"
                print("Posting to Discord...")
                send_to_discord(discord_message)
            else:
                print("Less than 15 minutes left or already within reset time window.")

            # Wait until the full reset time
            remaining_reset_time = wait_time - 900  # Remaining time post 15-min wait
            if remaining_reset_time > 0:
                time.sleep(remaining_reset_time)

            # Trigger reset
            stop_server()
            time.sleep(120)
            threading.Thread(target=start_batch_script, daemon=True).start()
        else:
            time.sleep(60)  # Re-check every minute if reset is not enabled




def create_gui():
    """Create the Tkinter GUI."""
    global text_area_main, text_area_all, text_area_warning, text_area_error, text_area_join_code
    global reset_enabled, reset_interval, reset_start_time

    window = tk.Tk()
    window.title("Output Monitor")
    notebook = ttk.Notebook(window)
    notebook.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    tab_main = tk.Frame(notebook)
    tab_all = tk.Frame(notebook)
    tab_warning = tk.Frame(notebook)
    tab_error = tk.Frame(notebook)
    tab_join_code = tk.Frame(notebook)
    tab_reset = tk.Frame(notebook)

    notebook.add(tab_main, text="Main")
    notebook.add(tab_all, text="All")
    notebook.add(tab_warning, text="Warnings")
    notebook.add(tab_error, text="Errors")
    notebook.add(tab_join_code, text="Join Codes")
    notebook.add(tab_reset, text="Reset Settings")

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

    def save_reset_settings():
        global reset_enabled, reset_interval, reset_start_time
        reset_enabled = reset_enabled_var.get()
        reset_interval = reset_interval_var.get()
        reset_start_time = datetime.strptime(reset_start_time_var.get(), "%H:%M").time()
    
        # Print the save confirmation message
        print(f"Reset scheduling updated: Enabled={reset_enabled}, Interval={reset_interval}, Start Time={reset_start_time.strftime('%H:%M')}")
    
        # Compute and print the next reset information immediately after saving settings
        now = datetime.now()
        next_reset = datetime.combine(now.date(), reset_start_time)
    
        # Ensure next_reset is in the future based on interval calculations
        while next_reset < now:
            next_reset += timedelta(hours=reset_interval)
    
        wait_time = (next_reset - now).total_seconds()
        hours, remainder = divmod(wait_time, 3600)
        minutes, _ = divmod(remainder, 60)
    
        # This message gets printed immediately after clicking Save Settings
        message = f"Next reset scheduled in: {int(hours)} hours and {int(minutes)} minutes at {next_reset.strftime('%I:%M %p')}."
        print(message)  # Print this message to console
        update_text_widget(message, "all")


    ttk.Button(tab_reset, text="Save Settings", command=save_reset_settings).pack(pady=5)

    stop_button = tk.Button(window, text="Stop Server", command=stop_server)
    stop_button.pack(padx=10, pady=10)
    start_button = tk.Button(window, text="Start Server", command=lambda: threading.Thread(target=start_batch_script, daemon=True).start())
    start_button.pack(padx=10, pady=10)

    threading.Thread(target=schedule_resets, daemon=True).start()
    window.mainloop()


if __name__ == "__main__":
    create_gui()
