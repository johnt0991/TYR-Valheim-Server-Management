import subprocess
import time
import ctypes
import pyautogui
import tkinter as tk
from tkinter import scrolledtext
from tkinter import ttk
import threading
import requests
import psutil
from datetime import datetime, timedelta
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

# Active processes list
active_processes = []

# Reset scheduling variables
reset_enabled = False
reset_interval = 6  # Default reset interval in hours
reset_start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).time()
next_reset_time = None

program_running = True
window = None


def send_to_sys_tab(message):
    """Send a message to the console output text box."""
    if text_area_console:  #if widget exists
        text_area_console.insert(tk.END, message + "\n") #insert message and then new line
        text_area_console.yview(tk.END)

def send_to_process_tab(message):
    """Sends an opened process to the processes tab"""
    if text_area_processes: #if widget exists
        time_stamp = str(datetime.now())
        text_area_processes.insert(tk.END, message + " " + time_stamp + "\n") #insert new message and then new line
        text_area_processes.yview(tk.END)

def send_to_discord(message):
    """Send a message to Discord using a webhook."""
    if not WEBHOOK_URL:
        print("Webhook URL not set.")
        return
    payload = {"content": message}
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"Failed to send message: {response.status_code}, {response.text}")
    else: send_to_sys_tab("Message Successfully Posted to Discord.")
        
def start_batch_script():
    """Runs the .bat script and captures the output."""
    global process, server_running, session_name, join_code, server_ip
    
    # Start the .bat script
    process = subprocess.Popen(
        BAT_SCRIPT_PATH,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        shell=False
    )
    server_running = True
    send_to_process_tab("Subprocess for valheim_server.exe started.")
    
    # Add process to active processes
    active_processes.append(process)
    update_active_processes()

    if reset_enabled and next_reset_time:
        send_to_sys_tab(f"The server has started. The next scheduled reset is at: {next_reset_time}")

    # Monitor the server output line-by-line
    for line in process.stdout:
        print(line.strip())
        update_text_widget(line.strip(), "all")
        
        # Handle warnings and errors
        if "WARNING" in line:
            update_text_widget(line.strip(), "warning")
        elif "ERROR" in line:
            update_text_widget(line.strip(), "error")

        # Extract session name and join code dynamically
        session_match = re.search(r'Session "(.*?)" registered with join code', line)
        if session_match:
            session_name = session_match.group(1)  # Extract session name
            join_code = line.split(' ')[-1]  # Extract join code
            message = f"The server has started.\nSession Name: {session_name}.  Session join code: {join_code}"
            send_to_discord(message)
            update_text_widget(message, "join_code")
            update_server_info(line.strip())

        # Extract server IP dynamically
        if "This is the serverIP used to register the server" in line:
            server_ip = line.split(': ')[-1]  # Extract the server IP
            update_server_info(line.strip())

    server_running = False
    update_server_info("Server has stopped.")
    
    # Remove process from active processes once it is stopped
    active_processes.remove(process)
    update_active_processes()

def update_active_processes():
    """Update the Active Processes tab."""
    def update_gui():
        text_area_processes.delete(1.0, tk.END)  # Clear the previous list
        for proc in active_processes:
            text_area_processes.insert(tk.END, f"Process PID: {proc.pid} started at {datetime.now()}\n")
        text_area_processes.yview(tk.END)

    # Schedule the update to happen in the main thread
    window.after(0, update_gui)


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
        # Get the process ID of the valheim_server.exe process
        for proc in psutil.process_iter(attrs=['pid', 'name']):
            if "valheim_server.exe" in proc.info['name']:
                pid = proc.info['pid']
                break
        
        # Use ctypes to send CTRL+C (CTRL_C_EVENT) to the process
        if pid:
            ctypes.windll.kernel32.GenerateConsoleCtrlEvent(0, pid)  # 0 is CTRL_C_EVENT

            # Optionally, wait and send 'y' (simulating confirmation)
            time.sleep(5)
            pyautogui.write('y')
            pyautogui.press('enter')

            print(f"Sent CTRL+C (CTRL_C_EVENT) to process {pid}.")
        else:
            print("Process not found.")
    except Exception as e:
        print(f"Error stopping the server: {e}")
    
    # Stop the process explicitly if needed
    global process
    if process:
        process.terminate()
        process.wait()  # Ensure the process is terminated
    update_active_processes()

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
    global reset_enabled, reset_interval, reset_start_time, next_reset_time, program_running
    while program_running:  # This ensures the loop will stop when the program ends
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

            send_to_discord("Server is restarting. Please wait until the server is back up to reconnect.")
            print("Server is restarting")
            stop_server()

            # Track reset thread as an active process (even though it's not a subprocess)
            reset_process = threading.Thread(target=start_batch_script, daemon=True)
            
            # Add the thread to the active threads list
            active_processes.append(reset_process)
            
            # Manually treat the thread as an active process
            send_to_process_tab(f"Scheduled reset subprocess started (Thread ID: {reset_process.ident}, Name: {reset_process.name}).")

            reset_process.start()

            # Wait for the thread to complete before removing it
            reset_process.join()  # This blocks the current thread until reset_process finishes

            time.sleep(120)  # Wait 2 minutes to ensure the server is stopped before restarting
        else:
            # If reset scheduling is disabled, sleep briefly before checking again
            time.sleep(60)
            
            # Remove the thread from the active threads list after it finishes
            active_processes.remove(reset_process)

def apply_reset_settings(interval_var, start_time_var):
    """Apply the reset settings and log the changes."""
    global reset_interval, reset_start_time, next_reset_time
    reset_interval = interval_var.get()
    reset_start_time = datetime.strptime(start_time_var.get().strip(), "%I:%M %p").time()
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

def clear_text_boxes():
    """Clears all scrolled text areas."""
    text_area_all.delete(1.0, tk.END)
    text_area_warning.delete(1.0, tk.END)
    text_area_error.delete(1.0, tk.END)
    text_area_join_code.delete(1.0, tk.END)
    text_area_console.delete(1.0, tk.END)
    text_area_processes.delete(1.0, tk.END)
    
    
def on_window_close():
    """Handle the window close event."""
    global program_running, window
    
    # Send the message immediately
    send_to_process_tab("Closing program, please wait")
    
    # Force the GUI to update before the window is destroyed
    window.update_idletasks()
    
    # Stop the reset schedule loop
    program_running = False
    
    # Schedule window destruction after 5 seconds
    def close_program():
        window.destroy()  # Close the window
    
    # Wait for 5 seconds before closing the window
    window.after(3000, close_program)

def create_gui():
    """Create the Tkinter GUI."""
    global window, text_area_main, text_area_all, text_area_warning, text_area_error, text_area_join_code, text_area_console, text_area_processes, program_running

    window = tk.Tk()
    window.title("Tyr VSM")
    window.protocol("WM_DELETE_WINDOW", on_window_close)
    notebook = ttk.Notebook(window)
    notebook.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    tab_main = tk.Frame(notebook)
    tab_reset = tk.Frame(notebook)
    tab_webhook = tk.Frame(notebook)
    tab_join_code = tk.Frame(notebook)
    tab_all = tk.Frame(notebook)
    tab_warning = tk.Frame(notebook)
    tab_error = tk.Frame(notebook)
    tab_console = tk.Frame(notebook)
    tab_active_processes = tk.Frame(notebook)

    notebook.add(tab_main, text="Session Info")
    notebook.add(tab_reset, text="Restart Settings")
    notebook.add(tab_webhook, text="Webhook Settings")
    notebook.add(tab_join_code, text="Join Codes")
    notebook.add(tab_all, text="All Messages")
    notebook.add(tab_warning, text="Warnings")
    notebook.add(tab_error, text="Errors")
    notebook.add(tab_console, text="Console Printout")  
    notebook.add(tab_active_processes, text="Processes")

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
    text_area_console = scrolledtext.ScrolledText(tab_console, width=80, height=20, wrap=tk.WORD)
    text_area_console.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_processes = scrolledtext.ScrolledText(tab_active_processes, width=80, height=20, wrap=tk.WORD)
    text_area_processes.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

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


    def generate_half_hour_intervals():
        intervals = []
        for hour in range(0, 24):
            for minute in [0, 30]:
                # Convert hour to 12-hour format and append AM/PM
                period = "AM" if hour < 12 else "PM"
                display_hour = hour % 12 if hour % 12 != 0 else 12
                intervals.append(f"{display_hour:02}:{minute:02} {period}")
        return intervals


    half_hour_intervals = generate_half_hour_intervals()
    ttk.Label(tab_reset, text="Reset Start Time:").pack()
    reset_start_time_dropdown = ttk.Combobox(tab_reset, textvariable=reset_start_time_var, values=half_hour_intervals, state='disabled')
    reset_start_time_dropdown.pack(pady=5)
    reset_start_time_dropdown.current(0)

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
    
    start_button = tk.Button(button_frame, text="Start Server", command=lambda: threading.Thread(target=start_batch_script, daemon=True).start())
    start_button.pack(side=tk.LEFT, padx=5)

    stop_button = tk.Button(button_frame, text="Stop Server", command=stop_server)
    stop_button.pack(side=tk.LEFT, padx=5)
    
    clear_button = tk.Button(button_frame, text="Clear All", command=clear_text_boxes)
    clear_button.pack(side=tk.LEFT, padx=5)

    threading.Thread(target=schedule_resets, daemon=True).start()
    window.mainloop()

if __name__ == "__main__":
    create_gui()
