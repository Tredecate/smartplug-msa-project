import json
import logging.config

from pathlib import Path
from asyncio import gather as asyncio_gather, run as asyncio_run

import httpx
import connexion
from connexion import NoContent
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

from config_handler import APP_CONFIG, API_CONFIG, CHECKLIST_CONFIG, LOG_CONFIG, ENV_CONFIG


##### ENDPOINTS #####
def health():
    logger.debug("Received health check request")
    return (NoContent, 200)


def get_stats():
    logger.info("GET /stats request received")

    # Read statuses from disk
    service_stats = read_dict_from_file(APP_CONFIG["stats_file"])

    # Error if service_stats is somehow empty without a last_updated timestamp
    if not service_stats:
        logger.error("Stats file is nonexistent, empty, or malformed")
        return ({"message": "Stats not yet recorded"}, 404)
    
    logger.debug(f"Returning service stats: {service_stats}")

    # Return service_stats dict
    return (service_stats, 200)


def update_stats():
    logger.info("PUT /update request received")

    # Go fish
    statuses, service_count = asyncio_run(fetch_data())
    logger.info(f"Fetched {service_count} stats results")

    # Write to disk
    write_dict_to_file(APP_CONFIG["stats_file"], statuses)

    # Return success
    return ({"service_count": service_count}, 201)


##### STATUS CHECK FUNCTIONS #####
async def fetch_data() -> tuple[dict, int]:
    # Fish basket
    responses = {}
    services, urls = zip(*CHECKLIST_CONFIG.items())

    try:
        # Fishing rod
        async with httpx.AsyncClient() as client:
            # Gone fishing
            tasks = [client.get(url, timeout=APP_CONFIG["stats_timeout_secs"]) for url in urls]
            results = await asyncio_gather(*tasks, return_exceptions=True)

            for res, service in zip(results, services):
                if isinstance(res, httpx.TimeoutException):
                    # Bad fish
                    logger.info(f"{service.capitalize()} is Not Available")
                    responses[service] = "Unavailable"
                else:
                    # Good fish
                    logger.debug(f"Fetched data from {service} with status code {res.status_code}")
                    responses[service] = parse_stats_response(res, service.capitalize())
        
    except Exception as e:
        # If anything broke, error and return empty
        logger.error(f"Data fetch failed unexpectedly! {e}")
        return responses, len(responses) - list(responses.values()).count("Unavailable")
    
    # Return the fish--uhhhhh stats
    return responses, len(responses) - list(responses.values()).count("Unavailable")


def parse_stats_response(response: httpx.Response, service_name: str) -> str:
    if response.status_code == 200:
        response_json = response.json()

        # If it's from receiver, it will have a status_datetime instead of event counts
        if "status_datetime" in response.json():
            return f"{service_name} is healthy at {response.json()['status_datetime']}"
        
        # Otherwise, it'll be a stats response with event counts, so grab 'em
        num_energy_events = response_json.get("num_energy_events", response_json.get("num_energy_readings", None))
        num_temperature_events = response_json.get("num_temperature_events", response_json.get("num_temp_readings", None))

        # If we've got None for either of the expected fields, something's wrong with the response
        if None in [num_energy_events, num_temperature_events]:
            logger.info(f"Stats response from {service_name} is missing expected fields: {response_json}")
            return "Unavailable"

        # Otherwise, return a nice message with the counts :D
        logger.info(f"{service_name} is Healthy")
        return f"{service_name} has {num_energy_events} Energy and {num_temperature_events} Temperature events"
    
    else:
        logger.info(f"{service_name} returning non-200 response")
        return "Unavailable"


##### UTIL FUNCTIONS #####
def read_dict_from_file(file_name: str) -> dict:
    # If the file doesn't exist, return an empty dict
    if not Path(file_name).is_file():
        return {}
    
    try:
        # If the file DOES exist: read, parse, and return
        with open(Path(file_name), 'r') as json_file:
            return json.load(json_file)
    except Exception:
        # If the file is malformed or inaccessible, return an empty dict
        return {}


def write_dict_to_file(file_name: str, content: dict):
    # Make sure parent directories exist
    Path(file_name).parent.mkdir(parents=True, exist_ok=True)
    
    # Open file_name in write mode
    with open(Path(file_name), "w") as json_file:
        # Parse dict to JSON and dump it to disk
        json.dump(content, json_file)


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
    app.run(port=APP_CONFIG["port"], host=APP_CONFIG["host"])