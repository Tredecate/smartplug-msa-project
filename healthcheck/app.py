import json
import logging.config

from pathlib import Path
from datetime import datetime, timezone, timedelta
from asyncio import gather as asyncio_gather, run as asyncio_run

import httpx
import connexion
from connexion import NoContent
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

from config_handler import APP_CONFIG, API_CONFIG, CHECKLIST_CONFIG, LOG_CONFIG, ENV_CONFIG


##### ENDPOINTS #####
def health():
    logger.debug("Received health check request")
    return (NoContent, 200)


def get_statuses():
    logger.info("GET /status request received")

    # Read health statuses from disk
    health_statuses = read_dict_from_file(APP_CONFIG["health_status_file"])
    last_updated = health_statuses.pop("last_updated", None)

    # Error if health_statuses is somehow empty without a last_updated timestamp
    if not health_statuses:
        logger.error("Health status file is nonexistent, empty, or malformed")
        return ({"message": "Health statuses not yet recorded"}, 404)
    
    logger.debug(f"Returning health statuses: {health_statuses}")

    # Return health_statuses dict
    return ({"health_statuses": health_statuses, "last_update": last_updated}, 200)


##### HEALTH CHECK FUNCTIONS #####
def update_health_statuses():
    logger.info("Periodic health checks triggered")

    # Go fish
    statuses = asyncio_run(fetch_data())
    logger.info(f"Fetched {len(statuses)} health check results")

    # Append a timestamp to the health status dict
    statuses["last_updated"] = datetime.now(timezone.utc).isoformat()

    # Write to disk
    write_dict_to_file(APP_CONFIG["health_status_file"], statuses)


async def fetch_data() -> dict:
    # Fish basket
    responses = {}
    services, urls = zip(*CHECKLIST_CONFIG.items())

    try:
        # Fishing rod
        async with httpx.AsyncClient() as client:
            # Gone fishing
            tasks = [client.get(url, timeout=APP_CONFIG["healthcheck_timeout_secs"]) for url in urls]
            results = await asyncio_gather(*tasks, return_exceptions=True)

            for res, service in zip(results, services):
                if isinstance(res, Exception):
                    # Bad fish
                    logger.error(f"Health check for {service} failed: {res}")
                    responses[service] = "Down"
                else:
                    # Good fish
                    logger.debug(f"Fetched data from {service} with status code {res.status_code}")
                    responses[service] = "Up" if res.status_code == 200 else "Down"
        
    except Exception as e:
        # If anything broke, error and return empty
        logger.error(f"Data fetch failed! {e}")
        return {}
    
    # Return the fish--uhhhhh healthchecks
    return responses


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
        func=           update_health_statuses, 
        trigger=        'interval', 
        seconds=        APP_CONFIG["healthcheck_interval_secs"], 
        next_run_time=  datetime.now() + timedelta(seconds=2)
    )

    scheduler.start()


##### INIT #####
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger("basicLogger")


app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])

app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"],
            base_path=API_CONFIG["base_path"])

if ENV_CONFIG.get("CORS_ALLOW_ALL", "false").lower() in ["true", "1", "yes", "y"]:
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
else:
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