import os.path
import json
import connexion
from connexion import NoContent
from datetime import datetime

MAX_BATCH_EVENTS = 5
ENERGY_FILE = "energy_consumption.json"
OP_TEMP_FILE = "operating_temperature.json"
ONE_PASS_UPDATE = True # Does OPEN/READ/WRITE/CLOSE instead of OPEN/READ/CLOSE -> OPEN/WRITE/CLOSE


def report_energy_consumption_readings(body: dict) -> tuple[object, int]:
    # INIT
    current_time = datetime.now()

    batch_summary = {}
    num_readings = len(body["readings"])

    # LOOP AND AGGREGATE
    sum_energy = 0
    count_switched_on = 0
    
    for reading in body["readings"]:
        sum_energy += reading["energy_consumed_watt_minutes"]
        count_switched_on += 1 if reading["switch_state"] == "ON" else 0
    
    # CALCULATE AND STORE
    batch_summary["num_consumption_readings"] = num_readings
    batch_summary["average_energy_consumed"] = sum_energy / num_readings
    batch_summary["percent_switched_on"] = count_switched_on / num_readings
    batch_summary["received_timestamp"] = current_time.isoformat(timespec='seconds')

    # READ, UPDATE, AND WRITE
    if ONE_PASS_UPDATE:
        one_pass_read_write(ENERGY_FILE, batch_summary, calc_energy_data)
        return (NoContent, 201)
    else:
        save_data = read_dict_from_file(ENERGY_FILE)
        save_data = calc_energy_data(save_data, batch_summary)

        write_dict_to_file(ENERGY_FILE, save_data)
        
        # RETURN
        return (NoContent, 201)


def report_internal_temp_readings(body: dict) -> tuple[object, int]:
    # INIT
    current_time = datetime.now()

    batch_summary = {}
    num_readings = len(body["readings"])
    
    # LOOP AND AGGREGATE
    sum_temperatures = 0
    count_abnormal = 0
    
    for reading in body["readings"]:
        sum_temperatures += reading["internal_temp_celsius"]
        count_abnormal += 0 if reading["thermal_status"] == "NORMAL" else 1
    
    # CALCULATE AND STORE
    batch_summary["num_temp_readings"] = num_readings
    batch_summary["average_internal_temp"] = sum_temperatures / num_readings
    batch_summary["percent_abnormal_thermals"] = count_abnormal / num_readings
    batch_summary["received_timestamp"] = current_time.isoformat(timespec='seconds')

    # READ, UPDATE, AND WRITE
    if ONE_PASS_UPDATE:
        one_pass_read_write(OP_TEMP_FILE, batch_summary, calc_temp_data)
        return (NoContent, 201)
    else:
        save_data = read_dict_from_file(OP_TEMP_FILE)
        save_data = calc_temp_data(save_data, batch_summary)

        write_dict_to_file(OP_TEMP_FILE, save_data)
        
        # RETURN
        return (NoContent, 201)


def calc_energy_data(save_data: dict, batch_summary: dict) -> dict:
    save_data["num_consumption_batches"] = save_data.get("num_consumption_batches", 0) + 1
    save_data["recent_batch_data"] = update_batch_queue(save_data.get("recent_batch_data", []), batch_summary)
    return save_data # I think editing in place might be fine, but return because why not


def calc_temp_data(save_data: dict, batch_summary: dict) -> dict:
    save_data["num_temp_batches"] = save_data.get("num_temp_batches", 0) + 1
    save_data["recent_batch_data"] = update_batch_queue(save_data.get("recent_batch_data", []), batch_summary)
    return save_data


def update_batch_queue(batch_queue: list, new_batch_summary: dict) -> list[dict]:
    # Reset batch_queue if it ain't a list (shouldn't happen, but was null once during dev)
    if not isinstance(batch_queue, list):
        batch_queue = []

    # Append the latest batch summary
    batch_queue.append(new_batch_summary)

    # Pop the oldest batch summary if we're over-length
    if len(batch_queue) > MAX_BATCH_EVENTS:
        batch_queue.pop(0)
    
    # Return
    return batch_queue


def read_dict_from_file(file_name: str) -> dict:
    # If the file doesn't exist, return an empty dict
    if not os.path.isfile(file_name):
        return {}
    
    try:
        # If the file DOES exist: read, parse, and return
        with open(file_name, 'r') as json_file:
            return json.load(json_file)
    except:
        # If the file is malformed or inaccessible, return an empty dict
        return {}


def write_dict_to_file(file_name: str, content: dict):
    # Open file_name in write mode
    with open(file_name, "w") as json_file:
        # Parse dict to JSON and dump it to disk
        json.dump(content, json_file)


def one_pass_read_write(file_name: str, batch_summary: dict, calc_data_func: callable):
    # Ensure the file exists
    if not os.path.isfile(file_name):
        with open(file_name, 'w') as json_file:
            json.dump({}, json_file)
    
    # Open up the file in update mode
    with open(file_name, 'r+') as json_file:
        # Read and figure out new data
        save_data = calc_data_func(json.load(json_file), batch_summary)

        # Write back to file
        json_file.seek(0)
        json.dump(save_data, json_file)
        json_file.truncate()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)