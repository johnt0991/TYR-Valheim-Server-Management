# %% Modules
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
from tkinter import messagebox
import signal
import pexpect
# %%
# %% Global Variables

BAT_SCRIPT_PATH = "start_headless_server.bat"
WEBHOOK_URL = ""
session_name = ""
server_ip = ""
join_code = ""
server_running = False
process = None  # To hold the reference to the running process
reset_enabled = False
reset_interval = 6  # Default reset interval in hours
reset_start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).time()
next_reset_time = None
program_running = True
window = None
timer_active = False
print("message check 1")
active_processes = []
port_num_var = 2456

# %%
# %% Message Posting Functions

def send_to_action_tab(message):
    if text_area_action:  #if widget exists
        time_stamp = datetime.now().strftime("%H:%M:%S")
        text_area_action.insert(tk.END, message + " " + time_stamp + "\n")
        text_area_action.yview(tk.END)

def send_to_discord(message):
    if not WEBHOOK_URL:
        print("Webhook URL not set.")
        return
    payload = {"content": message}
    response = requests.post(WEBHOOK_URL, json=payload)
    if response.status_code != 204:
        print(f"Failed to send message: {response.status_code}, {response.text}")
    else: send_to_action_tab("Message Successfully Posted to Discord.")
    
def update_server_info(line):
    server_info = f"Session: {session_name}\nServer IP: {server_ip}\nJoin Code: {join_code}\n"
    text_area_main.delete(1.0, tk.END)
    text_area_main.insert(tk.END, server_info)

def update_text_widget(message, filter_type):
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
        
def restart_reminder():
    global countdown_timer
    if countdown_timer == 900:
        send_to_discord("15 Minutes until next restart")
        send_to_action_tab("15 Minutes until next restart")
    if countdown_timer == 600:
        send_to_discord("10 Minutes until next restart")
        send_to_action_tab("10 Minutes until next restart")
    if countdown_timer == 300:
        send_to_discord("5 Minutes until next restart.")
        send_to_action_tab("5 Minutes until next restart")

def pop_up_warning(message):
    messagebox.showinfo("Notice:", message)
# %%
        
# %% Server Run Functions
def start_batch_script():
    global process, server_running, session_name, join_code, server_ip, server_command
    
    server_command = [
        "valheim_server", 
        "-nographics", 
        "-batchmode", 
        "-name", "Nufu Gaming", 
        "-port", "2456", 
        "-world", "Gaseoy", 
        "-password", "nf1234", 
        "-crossplay"
    ]    
    # Start the .bat script
    process = subprocess.Popen(server_command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    server_running = True
    
    # Add process to active processes
    active_processes.append(process)

    if reset_enabled and next_reset_time:
        send_to_action_tab(f"The server has started. The next scheduled reset is at: {next_reset_time}")

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
        session_match = re.search(r'Session "(.*?)" with join code (\d+)', line)
        if session_match:
            session_name = session_match.group(1)  # Extract session name
            join_code = session_match.group(2)  # Extract join code
            message = f"The server has started.\nSession Name: {session_name}.  Session join code: {join_code}"
            send_to_discord(message)
            update_text_widget(message, "join_code")
            update_server_info(line.strip())

        # Extract server IP dynamically
        if "This is the serverIP used to register the server" in line:
            server_ip = line.split(': ')[-1]  # Extract the server IP
            update_server_info(line.strip())
            
def stop_server():
    global process, server_running
    if process:
        try:
            # Attempt graceful shutdown with Ctrl+C (using pexpect for better control)
            process.sendcontrol('c')  # Send Ctrl+C
            process.expect(pexpect.EOF, timeout=30)  # Wait for server to exit
        except:
            # Fallback to terminate() if Ctrl+C fails
            process.terminate()
        process.wait()

        server_running = False
        send_to_action_tab("Server has successfully stopped.")
        active_processes.remove(process)
        clear_console_boxes()
    else:
        send_to_action_tab("Process not found.")


# %%
# %% Reset Scheduling
def enable_reset(reset_checkbox, reset_interval_entry, reset_start_time_dropdown, apply_button):
    global reset_enabled, cancel_timer_button
    if reset_checkbox.instate(['selected']):
        reset_interval_entry.config(state='normal')
        reset_start_time_dropdown.config(state='normal')
        apply_button.config(state='normal')
        cancel_timer_button.config(state='normal')
        reset_enabled = True
        send_to_action_tab("Reset scheduling enabled.")
    else:
        reset_interval_entry.config(state='disabled')
        reset_start_time_dropdown.config(state='disabled')
        apply_button.config(state='disabled')
        cancel_timer_button.config(state='disabled')
        reset_enabled = False
        send_to_action_tab("Reset scheduling disabled.")
    print("completed enable_reset")
        
def apply_reset_settings(interval_var, start_time_var):
    if server_running:
        if reset_enabled:
            global reset_interval, reset_start_time, next_reset_time, time_to_wait, timer_active, apply_button
            apply_button.config(state='disabled')
            reset_interval = interval_var.get()
            reset_start_time = datetime.strptime(start_time_var.get().strip(), "%I:%M %p").time()
            send_to_action_tab(f"Reset settings applied. Interval: {reset_interval} hours, Start Time: {reset_start_time}.")
            timer_active = True
            set_restart_time()
            print("completed apply_reset_settings")
        else:
            pop_up_warning("Reset not enabled.  No changes saved.")
    else:
        pop_up_warning("Server is not live.  Please start server before scheduling a reset.")
    
def set_restart_time():   
    global time_to_wait, timer_active
    now = datetime.now().replace(microsecond=0)
    next_reset = datetime.combine(now.date(), reset_start_time)
    while next_reset <= now:
        next_reset += timedelta(hours=reset_interval)

    next_reset_time = next_reset
    time_to_wait = int((next_reset - now).total_seconds())
    timer_active = True
    countdown_thread = threading.Thread(target=update_countdown, daemon=True) 
    countdown_thread.start() 
    send_to_action_tab(f"Next reset will occur at: {next_reset_time}")
    print(f"{time_to_wait}")
    print("completed set_restart_time")
    
def update_countdown():
    global time_to_wait, countdown_label, countdown_timer, time_active
    countdown_timer = time_to_wait
    while timer_active:
            while countdown_timer > 0:
                hours, remainder = divmod(countdown_timer, 3600)
                minutes, seconds = divmod(remainder, 60)
                hours = int(hours)  # Convert hours to integer
                minutes = int(minutes)  # Convert minutes to integer
                seconds = int(seconds)
                countdown_label.config(text=f"Time until next reset: {hours:02d}:{minutes:02d}:{seconds:02d}")
                print(countdown_timer)
                restart_reminder()
                time.sleep(1)
                countdown_timer -= 1
            if timer_active:
                countdown_label.config(text="Reset in Progress.  Please Wait")
                restart_server()
                set_restart_time()
            
    time_to_wait = 9999
    countdown_label.config(text=f"No Current Scheduled Reset.  current time to wait set at {countdown_timer}")

def restart_server():
    global reset_enabled, reset_interval, reset_start_time, next_reset_time, program_running, server_running, time_to_wait
    if reset_enabled:
        send_to_discord("Server is restarting. Please wait until the server is back up to reconnect.")
        send_to_action_tab("Server is restarting")
        try:
            stop_server()
            send_to_action_tab("Server successfully shut down.  Will begin reboot in 30 seconds.")
            time.sleep(30)
            send_to_action_tab("Beginning Server Reboot.")
            start_batch_script()
        except Exception as e:
            send_to_action_tab(f"Error Restarting Server.  Please manually shut down. Error: {e}")
                
def cancel_timer():
    global timer_active, countdown_timer, apply_button
    timer_active = False
    countdown_timer = 0
    apply_button.config(state='normal')
    pop_up_warning("Reset Timer has been canceled.")
# %%

def apply_webhook_settings(webhook_url_var):
    global WEBHOOK_URL
    WEBHOOK_URL = webhook_url_var.get()
    send_to_action_tab(f"Webhook URL set to: {WEBHOOK_URL}")

def clear_text_boxes():
    """Clears all scrolled text areas."""
    text_area_all.delete(1.0, tk.END)
    text_area_warning.delete(1.0, tk.END)
    text_area_error.delete(1.0, tk.END)
    text_area_join_code.delete(1.0, tk.END)
    text_area_action.delete(1.0, tk.END)
    
def clear_console_boxes():
    """Clears all scrolled text areas."""
    text_area_warning.delete(1.0, tk.END)
    text_area_error.delete(1.0, tk.END)

   
    
def on_window_close():
    global program_running, window
    
    # Send the message immediately
    send_to_action_tab("Closing program, please wait")
    
    # Force the GUI to update before the window is destroyed
    window.update_idletasks()
    
    # Stop the reset schedule loop
    program_running = False
    
    # Schedule window destruction after 5 seconds
    def close_program():
        window.destroy()  # Close the window
    
    # Wait for 5 seconds before closing the window
    window.after(1000, close_program)
       
# %% GUI
def create_gui():
    global window, text_area_main, apply_button, server_command, port_num_var, text_area_all, cancel_timer_button, text_area_warning, text_area_error, text_area_join_code, text_area_action, text_area_processes, program_running, countdown_label

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
    tab_action = tk.Frame(notebook)

    notebook.add(tab_main, text="Session Info")
    notebook.add(tab_reset, text="Restart Settings")
    notebook.add(tab_webhook, text="Webhook Settings")
    notebook.add(tab_join_code, text="Join Codes")
    notebook.add(tab_all, text="All Messages")
    notebook.add(tab_warning, text="Warnings")
    notebook.add(tab_error, text="Errors")
    notebook.add(tab_action, text="Action Updates")  

    text_area_all = scrolledtext.ScrolledText(tab_all, width=80, height=20, wrap=tk.WORD)
    text_area_all.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_warning = scrolledtext.ScrolledText(tab_warning, width=80, height=20, wrap=tk.WORD)
    text_area_warning.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_error = scrolledtext.ScrolledText(tab_error, width=80, height=20, wrap=tk.WORD)
    text_area_error.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_join_code = scrolledtext.ScrolledText(tab_join_code, width=80, height=20, wrap=tk.WORD)
    text_area_join_code.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
    text_area_action = scrolledtext.ScrolledText(tab_action, width=80, height=20, wrap=tk.WORD)
    text_area_action.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    session_name_label = ttk.Label(tab_main, text="Session Name:")
    session_name_label.grid(row=0, column=0, sticky="e", pady=10, padx=10)
    
    session_name_var = tk.StringVar()
    session_name_entry = ttk.Entry(tab_main, textvariable=session_name_var)
    session_name_entry.grid(row=0, column=1, stick="w")
    
    server_name_label = ttk.Label(tab_main, text="Server Name:")
    server_name_label.grid(row=1, column=0, sticky="e")
    
    server_name_var = tk.StringVar()
    server_name_entry = ttk.Entry(tab_main, textvariable=server_name_var)
    server_name_entry.grid(row=1, column=1, sticky="w")
    
    port_num_label = ttk.Label(tab_main, text="Port Number:")
    port_num_label.grid(row=2, column=0, sticky="e", pady=10)
    
    port_num_var = tk.StringVar(value=2456)
    port_num_entry = ttk.Entry(tab_main, textvariable=port_num_var)
    port_num_entry.grid(row=2, column=1, sticky="w")
    
    world_name_label = ttk.Label(tab_main, text="World Name:")
    world_name_label.grid(row=3, column=0, sticky="e")
    
    world_name_var = tk.StringVar()
    world_name_entry = ttk.Entry(tab_main, textvariable=world_name_var)
    world_name_entry.grid(row=3, column=1, sticky="w")
    
    password_label = ttk.Label(tab_main, text="Server Password:")
    password_label.grid(row=4, column=0, sticky="e", pady=10)
    
    password_var = tk.StringVar()
    password_entry = ttk.Entry(tab_main, textvariable=password_var)
    password_entry.grid(row=4, column=1, sticky="w")    

    reset_enabled_var = tk.BooleanVar()
    reset_interval_var = tk.IntVar(value=6)
    reset_start_time_var = tk.StringVar(value="00:00")

    reset_checkbox = ttk.Checkbutton(tab_reset, text="Enable Reset Scheduling", variable=reset_enabled_var,
        command=lambda: enable_reset(reset_checkbox, reset_interval_entry, reset_start_time_dropdown, apply_button)
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

    restart_button_frame = tk.Frame(tab_reset)
    restart_button_frame.pack(side=tk.TOP, pady=10)

    apply_button = tk.Button(restart_button_frame, text="Apply Settings", command=lambda: apply_reset_settings(reset_interval_var, reset_start_time_var), state=tk.DISABLED)
    apply_button.pack(side=tk.LEFT, padx=5)
        
    cancel_timer_button = tk.Button(restart_button_frame, text="Cancel Timer", command=cancel_timer, state=tk.DISABLED)
    cancel_timer_button.pack(side=tk.LEFT, padx=5)

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
    
    countdown_label = ttk.Label(button_frame, text="Time until next reset: 00:00:00")
    countdown_label.pack(side=tk.LEFT, padx=5)

    window.mainloop()

if __name__ == "__main__":
    create_gui()
# %%
