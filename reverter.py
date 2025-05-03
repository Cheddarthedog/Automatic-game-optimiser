import json
import subprocess
import logging
import os

LOG_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "logs", "reverter.log")
DEFAULT_VALUES_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config", "default_values.json")

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


def read_default_file():
    try:
        with open(DEFAULT_VALUES_FILE, "r") as file:
            config = json.load(file)
            return config
    except FileNotFoundError:
        logging.error("Config file not found, using default values.")
        return {}
    except json.JSONDecodeError:
        logging.error("Error decoding JSON from config file.")
        return {}
        
def revert_optimisations():
    config = read_default_file()
    if not config:
        logging.error("No configuration found, cannot revert optimisations.")
        return
    
    revert_cpu_governor(config)
    disable_zram(config)
    enable_screensaver_and_power_saving(config)
    revert_power_saving(config)
    logging.info("All optimisations reverted successfully.")

def revert_cpu_governor(config):
    cpu_governor = config.get("cpu_governor", "powersave")
    subprocess.run(["sudo", "cpupower", "frequency-set", "-g", cpu_governor], check=True, text=True)
    logging.info(f"CPU governor reverted to {cpu_governor}")

def disable_zram(config):
    zram_status = config.get("zram_status", "disabled")
    if zram_status == "enabled":
        subprocess.run(["sudo", "swapoff", "-a"], check=True)
        logging.info("ZRAM disabled")
    else:
        logging.info("ZRAM was not enabled, no action taken.")

def enable_screensaver_and_power_saving(config):
    if config.get("screensaver_enabled", True):
        subprocess.run(["gsettings", "set", "org.gnome.desktop.session", "idle-delay", str(config["screensaver_idle_delay"])], check=True)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.screensaver", "idle-activation-enabled", "true"], check=True)
        logging.info(f"Screensaver re-enabled with idle delay set to {config['screensaver_idle_delay']} seconds")
    else:
        subprocess.run(["gsettings", "set", "org.gnome.desktop.session", "idle-delay", "0"], check=True)
        subprocess.run(["gsettings", "set", "org.gnome.desktop.screensaver", "idle-activation-enabled", "false"], check=True)
        logging.info(f"Screensaver disabled")

def revert_power_saving(config):
    power_type = config.get("power_sleep_inactive_ac_type", "suspend")
    timeout = config.get("power_sleep_inactive_ac_timeout", 600)
    subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.power", "sleep-inactive-ac-type", power_type], check=True)
    subprocess.run(["gsettings", "set", "org.gnome.settings-daemon.plugins.power", "sleep-inactive-ac-timeout", str(timeout)], check=True)
    logging.info(f"Power saving settings reverted to type: {power_type} and timeout: {timeout} seconds")

if __name__ == "__main__":
    revert_optimisations()