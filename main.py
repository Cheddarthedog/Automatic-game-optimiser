import logging
import subprocess
import json
import time
import os

prev_pid = None
stable_duration = 0
threshold_time = 6
LOCK_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "tmp", "process_lock.tmp")
CURRENT_PROCESS_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "detection", "current_large_process.json")
OPTIMISER_LOCATION = os.path.join(os.path.dirname(os.path.realpath(__file__)), "optimiser.py")
LOG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs", "main.log")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Read the current large process from a JSON file
def read_logged_process():
    try:
        with open(CURRENT_PROCESS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    
# Lock process to prevent other processes from taking over
def create_lock(pid, name):
    if not os.path.exists(LOCK_FILE):
        with open(LOCK_FILE, "w") as f:
            json.dump({"pid": pid, "name": name}, f)

# Delete the lock file
def remove_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

# Check if lock file exists
def is_locked():
    return os.path.exists(LOCK_FILE)



    
if __name__ == "__main__":
    while True:
        current = read_logged_process()
        if current:
            pid = current["pid"]
            name = current["name"]
            if is_locked():
                print("Process is already being optimised.")
                time.sleep(2)
                continue
            if pid == prev_pid:
                stable_duration += 2
            else:
                stable_duration = 0
                prev_pid = pid
            if stable_duration >= threshold_time:
                print(f"Process {pid} has been stable for {stable_duration} seconds, triggering optimiser.")
                create_lock()
                try:
                # Call the optimiser script
                    subprocess.run(["python3", OPTIMISER_LOCATION], check=True)
                    logging.info(f"Optimiser script executed for process {pid}.")
                except subprocess.CalledProcessError as e:
                    logging.error(f"Failed to execute optimiser script: {e}")
                finally:
                    remove_lock()
        
        time.sleep(2)