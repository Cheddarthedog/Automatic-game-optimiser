import psutil
import time
import json
import logging
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs", "process_scanner.log")
CURRENT_LARGE_PROCESS = os.path.join(os.path.dirname(os.path.realpath(__file__)), "detection", "current_large_process.json")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def has_steam_or_proton_parent(proc):
    try:
        while proc:
            if proc.name() in ['steam.exe', 'steam.sh', 'steamwebhelper', 'steam', 'Steam', 'proton']:
                logging.info(f"Process {proc.pid} has Steam or Proton parent: {proc.name()}")
                return True
            proc = proc.parent()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        logging.error(f"Error accessing parent process: {proc}")
        return False
    return False

def get_heavy_processes():
    top_weight = 0
    top_proc = None
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
            cpu_usage = proc.info['cpu_percent']
            memory_usage = proc.info['memory_info'].rss / (1024 * 1024)
            if cpu_usage < 3 and memory_usage < 1024:
                continue
            if not has_steam_or_proton_parent(proc):
                continue
            weight = cpu_usage + memory_usage * 0.5
            if weight > top_weight:
                top_weight = weight
                top_proc = {
                'pid': proc.info['pid'],
                'name': proc.info['name'],
                'cpu_percent': cpu_usage,
                'memory_usage_mb': memory_usage
                }
                with open(CURRENT_LARGE_PROCESS, 'w') as f:
                    json.dump(top_proc, f, indent=4)
                logging.info(f"Heavy process found and recorded: {top_proc}")
        return top_proc
    except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
        logging.error(f"Error accessing process information: {e}")
        return None

if __name__ == "__main__":
    while True:
        result = get_heavy_processes()
        print(result)
        time.sleep(2)