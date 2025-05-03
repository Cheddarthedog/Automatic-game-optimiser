import psutil
import time
import json
import subprocess
import os
import logging

script_dir = os.path.dirname(os.path.realpath(__file__))

LOG_FILE = os.path.join(script_dir, "logs", "optimiser.log")
MEMORY_LOG_FILE = os.path.join(script_dir, "logs", "memory.log")
LOCK_FILE = os.path.join(script_dir, "tmp", "process_lock.tmp")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# Ensure the log directory exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(MEMORY_LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)

def read_locked_file():
    try:
        with open(LOCK_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"Lock file not found: {e}")
        return None
    
def set_cpu_governor(mode="performance"):
    try:
        subprocess.run(["sudo", "cpupower", "frequency-set", "-g", mode], check=True, text=True)
        logging.info(f"CPU governor set to {mode}")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to set CPU governor: {e}")

def log_memory_status(stage):
    mem = psutil.virtual_memory()
    with open(MEMORY_LOG_FILE, "a") as f:
        f.write(f"{stage} - RAM: total={mem.total}, available={mem.available}, used={mem.used}, percent={mem.percent}\n")
    logging.info(f"{stage} RAM: total={mem.total}, available={mem.available}, used={mem.used}, percent={mem.percent}")

def enable_zram():

    log_memory_status("Before enabling zram")

    try:
        with open("/proc/swaps", "r") as f:
            if "/dev/zram0" in f.read():
                logging.info("Zram is already enabled.")
                return

        subprocess.run(["sudo", "modprobe", "zram"], check=True)

        if not os.path.exists("/dev/zram0"):
            logging.warning("/dev/zram0 does not exist. Attepting to create it with sysfs.")
            with open("/sys/class/zram-control/hot_add", "w") as f:
                f.write("0")

        if not os.path.exists("/dev/zram0"):
            logging.error("Failed to create /dev/zram0. Please check your system configuration.")
            return

        subprocess.run(["sudo", "bash", "-c", "echo 1G > /sys/block/zram0/disksize"], check=True)
        subprocess.run(["sudo", "mkswap", "/dev/zram0"], check=True)
        subprocess.run(["sudo", "swapon", "/dev/zram0"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to enable zram: {e}")

    log_memory_status("After enabling zram")

def disable_screensaver_and_power_saving():
    try:
        subprocess.run(["gsettings", "set", "org.gnome.desktop.session", "idle-delay", "0"], check=True)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.screensaver", "idle-activation-enabled", "false"], check=True)
        subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.power", "sleep-inactive-ac-type", "nothing"], check=True)
        subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.power", "sleep-inactive-ac-timeout", "0"], check=True)
        logging.info("Screensaver and power saving disabled")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to disable screensaver and power saving: {e}")

    
def apply_optimisations(pid):
    try:
        p = psutil.Process(pid)

        p.nice(-10)  # Set process priority to high
        logging.info(f"Process {pid} priority set to high")

        subprocess.run(["ionice", "-c", "1", "-n", "0", "-p", str(pid)]) # Set I/O priority to high
        logging.info(f"Process {pid} I/O priority set to high")

        subprocess.run(["sudo", "chrt", "-f", "75", str(pid)])  # Set real-time scheduling policy
        logging.info(f"Process {pid} real-time scheduling policy set")

        set_cpu_governor("performance")  # Set CPU governor to performance

        enable_zram()  # Enable zram
        logging.info("Zram enabled")

        disable_screensaver_and_power_saving()  # Disable screensaver and power saving

    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to apply optimisations: {e}")
    except psutil.NoSuchProcess:
        logging.error(f"Process {pid} does not exist")



def monitor_process(pid):
    try:
        while psutil.pid_exists(pid):
            time.sleep(1)
        logging.info(f"Process {pid} has ended, reverting to chosen settings")
        subprocess.run(["python3", os.path.join(os.path.dirname(__file__), "reverter.py")], check=True)
    except psutil.NoSuchProcess:
        logging.error(f"Process {pid} does not exist or has been terminated unexpectedly")


if __name__ == "__main__":
    lock_info = read_locked_file()
    if lock_info:
        pid = lock_info["pid"]
        logging.info(f"Process locked, applying optimisations to PID: {pid}")
        apply_optimisations(pid)
        monitor_process(pid)
    else:
        logging.error(f"No process lock found, exiting.")