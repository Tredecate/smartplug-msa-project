import httpx
import connexion
from connexion import NoContent


DATABASE_URL = "http://localhost:8090/plug-data/"


def report_energy_consumption_readings(body: dict) -> tuple[object, int]:
    # INIT
    plug_data = {
        "plug_id": body["plug_id"],
        "plug_country": body.get("plug_country", None), # Non-required field
        "plug_uptime": body["plug_uptime"],
        "batch_timestamp": body["report_timestamp"]
    }

    if plug_data["plug_country"] is None:
        del plug_data["plug_country"]
    
    # LOOP AND POST
    for reading in body["readings"]:
        plug_data.update({
            "energy_consumed_watt_minutes": reading["energy_consumed_watt_minutes"],
            "switch_state": reading["switch_state"],
            "reading_timestamp": reading["reading_timestamp"],
        })

        res = httpx.post(DATABASE_URL + "energy-consumed", json=plug_data)

        if res.status_code != 201:
            return (NoContent, res.status_code)
    
    # RETURN
    return (NoContent, 201)


def report_internal_temp_readings(body: dict) -> tuple[object, int]:
    # INIT
    plug_data = {
        "plug_id": body["plug_id"],
        "plug_country": body.get("plug_country", None), # Non-required field
        "plug_uptime": body["plug_uptime"],
        "batch_timestamp": body["report_timestamp"]
    }

    if plug_data["plug_country"] is None:
        del plug_data["plug_country"]

    # LOOP AND POST
    for reading in body["readings"]:
        plug_data.update({
            "internal_temp_celsius": reading["internal_temp_celsius"],
            "thermal_status": reading["thermal_status"],
            "reading_timestamp": reading["reading_timestamp"],
        })

        res = httpx.post(DATABASE_URL + "internal-temp", json=plug_data)

        if res.status_code != 201:
            return (NoContent, res.status_code)
    
    # RETURN
    return (NoContent, 201)


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)