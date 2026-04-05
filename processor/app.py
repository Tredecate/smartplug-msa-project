import httpx
import json
import logging.config
import connexion

from pathlib import Path
from connexion import NoContent
from datetime import datetime, timezone, timedelta
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from config_handler import APP_CONFIG, API_CONFIG, STORAGE_CONFIG, LOG_CONFIG


##### ENDPOINTS #####
def health():
    logger.debug("Received health check request")
    return (NoContent, 200)


def get_stats():
    logger.info("GET /stats request received")

    # Read stats and remove unwanted fields
    stats_dict = read_dict_from_file(APP_CONFIG["stats_file"])
    stats_dict.pop("last_updated", None)

    # Error if stats_dict is somehow empty
    if not stats_dict:
        logger.error("Statistics file is nonexistent, empty, or malformed")
        return ({"message": "Statistics do not exist"}, 404)
    
    logger.debug(f"Returning stats: {stats_dict}")
    logger.info("GET /stats request completed")

    # Return stats_dict
    return (stats_dict, 200)


##### STATISTIC FUNCTIONS #####
def update_statistics():
    logger.info("Periodic statistics update triggered")

    # Read current stats and determine time range for new data
    current_stats = read_dict_from_file(APP_CONFIG["stats_file"])
    current_time = datetime.now(timezone.utc)
    latest_time = datetime.fromisoformat(current_stats.get("last_updated", APP_CONFIG["fallback_start_time"]))

    # Go fish
    energy_data, temp_data = fetch_data(latest_time + timedelta(microseconds=1), current_time)

    logger.info(f"Fetched {len(energy_data)} new energy records and {len(temp_data)} new temperature records")

    # Update stats and write to disk
    new_stats = calculate_stats(current_stats, energy_data, temp_data)
    write_dict_to_file(APP_CONFIG["stats_file"], new_stats)

    logger.info("Periodic statistics update completed")


def fetch_data(start_timestamp: datetime, end_timestamp: datetime) -> tuple[list[dict], list[dict]]:
    # Define query parameters for the time range
    timespan_params = {"start_timestamp": start_timestamp.isoformat(timespec='microseconds'), "end_timestamp": end_timestamp.isoformat()}

    try:
        # Gone fishing
        energy_res =    httpx.get(STORAGE_CONFIG["baseurl"] + STORAGE_CONFIG["endpoints"]["energy"],    params=timespan_params)
        temp_res =      httpx.get(STORAGE_CONFIG["baseurl"] + STORAGE_CONFIG["endpoints"]["temp"],      params=timespan_params)

        # Check for HTTP errors and log them
        if energy_res.status_code != 200:
            raise Exception(f"Error fetching energy data: {energy_res.status_code} {energy_res.text}")
        if temp_res.status_code != 200:
            raise Exception(f"Error fetching temperature data: {temp_res.status_code} {temp_res.text}")
        
    except Exception as e:
        # If anything broke, error and return empty
        logger.error(f"Data fetch failed! {e}")
        return ([], [])
    
    # Return the fish--uhhhhh data
    return (energy_res.json(), temp_res.json())


def calculate_stats(old_stats: dict, energy_data: list[dict], temp_data: list[dict]) -> dict:
    # Define a base dict with defaults
    base = {
        "num_energy_readings": 0,
        "min_energy_consumed": float('inf'),
        "max_energy_consumed": float('-inf'),
        "avg_energy_consumed": 0,

        "num_temp_readings": 0,
        "min_internal_temp": float('inf'),
        "max_internal_temp": float('-inf'),
        "avg_internal_temp": 0,

        "last_updated": APP_CONFIG["fallback_start_time"]
    }

    # Overlay old_stats on top of base to replace defaults with actual values (if they exist)
    base.update(old_stats)
    
    # Calculate cumulative reading counts
    total_energy_readings = len(energy_data) + base["num_energy_readings"]
    total_temp_readings = len(temp_data) + base["num_temp_readings"]
    
    # Extract datapoint lists from new readings
    new_energy_readings = [reading["energy_consumed_watt_minutes"] for reading in energy_data]
    new_temp_readings = [reading["internal_temp_celsius"] for reading in temp_data]
    new_timestamps = [datetime.fromisoformat(reading["date_created"]) for reading in energy_data + temp_data]

    # If we've got new energy readings...
    if new_energy_readings:
        energy_stats = {
            # Calculate cumulative stats using old stats and new readings
            "num_energy_readings": total_energy_readings,
            "min_energy_consumed": min([*new_energy_readings, base["min_energy_consumed"]]),
            "max_energy_consumed": max([*new_energy_readings, base["max_energy_consumed"]]),

            # Calculate new average using weighted average of old and new readings
            "avg_energy_consumed": (sum(new_energy_readings) + (base["avg_energy_consumed"] * base["num_energy_readings"])) / total_energy_readings
        }
    
    # If we've got new temp readings...
    if new_temp_readings:
        temp_stats = {
            # Calculate cumulative stats using old stats and new readings
            "num_temp_readings": total_temp_readings,
            "min_internal_temp": min([*new_temp_readings, base["min_internal_temp"]]),
            "max_internal_temp": max([*new_temp_readings, base["max_internal_temp"]]),

            # Calculate new average using weighted average of old and new readings
            "avg_internal_temp": (sum(new_temp_readings) + (base["avg_internal_temp"] * base["num_temp_readings"])) / total_temp_readings
        }

    new_stats = {
        # Write any stats we have to a new dict, prioritizing new stats
        **old_stats,
        **(energy_stats if new_energy_readings  else {}),
        **(temp_stats   if new_temp_readings    else {}),

        # Set last_updated to the latest timestamp from the new readings, or keep old if no new readings
        "last_updated": max([*new_timestamps, datetime.fromisoformat(base["last_updated"])]).isoformat()
    }
    
    logger.debug(f"Updated stats: {new_stats}" if new_stats != old_stats else "No stats changed")
    return new_stats


##### UTIL FUNCTIONS #####
def read_dict_from_file(file_name: str) -> dict:
    # If the file doesn't exist, return an empty dict
    if not Path(file_name).is_file():
        return {}
    
    try:
        # If the file DOES exist: read, parse, and return
        with open(Path(file_name), 'r') as json_file:
            return json.load(json_file)
    except:
        # If the file is malformed or inaccessible, return an empty dict
        return {}


def write_dict_to_file(file_name: str, content: dict):
    # Make sure parent directories exist
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)
    
    # Open file_name in write mode
    with open(Path(file_name), "w") as json_file:
        # Parse dict to JSON and dump it to disk
        json.dump(content, json_file)


##### SETUP SCHEDULER #####
def init_scheduler():
    scheduler = BackgroundScheduler(daemon=True)
    
    scheduler.add_job(
        func=           update_statistics, 
        trigger=        'interval', 
        seconds=        APP_CONFIG["proc_interval_secs"], 
        next_run_time=  datetime.now() + timedelta(seconds=2)
    )

    scheduler.start()


##### INIT #####
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("basicLogger")


app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])

app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"])

app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=API_CONFIG["cors"]["allow_origins"],
    allow_methods=API_CONFIG["cors"]["allow_methods"],
    allow_headers=API_CONFIG["cors"]["allow_headers"],
    allow_credentials=True,
)

if __name__ == "__main__":
    init_scheduler()
    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])