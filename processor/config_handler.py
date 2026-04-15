import yaml
from pathlib import Path
from os import environ


# UTIL FUNCTIONS
def overlay_dicts(base: dict, overlay: dict) -> dict:
    """
    Recursively overlays one dictionary onto another
    """
    # Go through key:value pairs in the overlay dict
    for key, value in overlay.items():
        # If value in both dict is a dict, recurse
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = overlay_dicts(base[key], value)
        else:
            # Otherwise just set the value
            base[key] = value
    return base


# LOAD DEFAULTS
# App config
try:
    with open(Path("./default.config/default.processor_app_conf.yml"), 'r') as f:
        default_app_config = yaml.safe_load(f)
except FileNotFoundError:
    default_app_config = {}

# Log config
try:
    with open(Path("./default.config/default.processor_log_conf.yml"), 'r') as f:
        default_log_config = yaml.safe_load(f)
except FileNotFoundError:
    default_log_config = {}


# LOAD CONFIGURATION
# App config
try:
    with open(Path("/config/processor_app_conf.yml"), 'r') as f:
        file_config = yaml.safe_load(f)
except FileNotFoundError:
    file_config = {}

# Log config
try:
    with open(Path("/config/processor_log_conf.yml"), 'r') as f:
        file_log_config = yaml.safe_load(f)
except FileNotFoundError:
    file_log_config = {}


# OVERLAY LOADED CONFIG OVER DEFAULTS
config_dict = overlay_dicts(default_app_config, file_config)
log_config_dict = overlay_dicts(default_log_config, file_log_config)

# CREATE LOG DIRECTORY
Path(log_config_dict["handlers"]["file"]["filename"]).parent.mkdir(parents=True, exist_ok=True)

# SET GLOBAL CONFIG VARIABLES
# App config
APP_CONFIG = config_dict["services"]["self"]
STORAGE_CONFIG = config_dict["services"]["storage"]
API_CONFIG = config_dict["api"]

# Log config
LOG_CONFIG = log_config_dict

# Env vars
ENV_CONFIG = environ.copy()