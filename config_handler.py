import yaml


# DEFAULT CONFIGURATION
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
            "port": 8090,
            "auto_create_tables": True,
            "db": {
                "protocol": "mysql",
                "username": "storage_service",
                "password": "$torage_5ervice",
                "host": "localhost",
                "database": "readings"
            }
        }
    }
}


# UTIL FUNCTIONS
def overlay_dicts(base: dict, overlay: dict) -> dict:
    """
    Recursively overlays one dictionary onto another
    """
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            base[key] = overlay_dicts(base[key], value)
        else:
            base[key] = value
    return base


# LOAD CONFIGURATION
try:
    with open("app_conf.yml", 'r') as f:
        file_config = yaml.safe_load(f)
except FileNotFoundError:
    file_config = {}

# OVERLAY LOADED CONFIG OVER DEFAULTS
config_dict = overlay_dicts(_DEFAULT_CONFIG, file_config)

# SET GLOBAL CONFIG VARIABLES
APP_CONFIG = config_dict["services"]["self"]
API_CONFIG = config_dict["api"]