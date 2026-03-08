import yaml
from pathlib import Path

# DEFAULT CONFIGURATIONS
_DEFAULT_CONFIG = {
    "version": 1,
    "api": {
        "file": "openapi.yml",
        "spec_dir": "./",
        "strict_validation": True,
        "validate_responses": True
    },
    "services": {
        "self": {
            "port": 8080
        },
        "broker": {
            "host": "localhost",
            "port": 9092,
            "topic": "events"
        }
    }
}

_DEFAULT_LOG_CONFIG = {
    "version": 1,
    "formatters": {
        "simple": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "filename": "./logs/app.log"
        }
    },
    "loggers": {
        "basicLogger": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["console"]
        }
    },
    "disable_existing_loggers": False
}


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


# LOAD CONFIGURATION
# App config
try:
    with open(Path("./config/app_conf.yml"), 'r') as f:
        file_config = yaml.safe_load(f)
except FileNotFoundError:
    file_config = {}

# Log config
try:
    with open(Path("./config/log_conf.yml"), 'r') as f:
        file_log_config = yaml.safe_load(f)
except FileNotFoundError:
    file_log_config = {}


# OVERLAY LOADED CONFIG OVER DEFAULTS
config_dict = overlay_dicts(_DEFAULT_CONFIG, file_config)
log_config_dict = overlay_dicts(_DEFAULT_LOG_CONFIG, file_log_config)


# CREATE LOG DIRECTORY
Path(log_config_dict["handlers"]["file"]["filename"]).parent.mkdir(parents=True, exist_ok=True)


# SET GLOBAL CONFIG VARIABLES
# App config
APP_CONFIG = config_dict["services"]["self"]
BROKER_CONFIG = config_dict["services"]["broker"]
API_CONFIG = config_dict["api"]

# Log config
LOG_CONFIG = log_config_dict