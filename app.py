import httpx
import asyncio
import uuid
import connexion
from connexion import NoContent


DATABASE_URL = "http://localhost:8090/plug-data"


async def report_energy_consumption_readings(body: dict) -> tuple[object, int]:
    # INIT
    plug_data = {
        "plug_id": body["plug_id"],
        "plug_country": body.get("plug_country", None), # Non-required field
        "plug_uptime": body["plug_uptime"],
        "batch_timestamp": body["report_timestamp"],
        "batch_trace_id": str(uuid.uuid4())
    }

    if plug_data["plug_country"] is None:
        del plug_data["plug_country"]
    
    # CREATE ASYNC TASKS
    async with httpx.AsyncClient() as client:
        tasks = []
        for reading in body["readings"]:
            reading_data = plug_data.copy()
            reading_data.update(reading)
            tasks.append(client.post(DATABASE_URL + "/energy-consumed", json=reading_data))
        
        # RUN ALL TASKS
        responses = await asyncio.gather(*tasks, return_exceptions=False)
        
        # CHECK STATUS CODES
        for res in responses:
            if res.status_code != 201:
                return (NoContent, res.status_code)
    
    # RETURN
    return (NoContent, 201)


async def report_internal_temp_readings(body: dict) -> tuple[object, int]:
    # INIT
    plug_data = {
        "plug_id": body["plug_id"],
        "plug_country": body.get("plug_country", None), # Non-required field
        "plug_uptime": body["plug_uptime"],
        "batch_timestamp": body["report_timestamp"],
        "batch_trace_id": str(uuid.uuid4())
    }

    if plug_data["plug_country"] is None:
        del plug_data["plug_country"]

    # CREATE ASYNC TASKS
    async with httpx.AsyncClient() as client:
        tasks = []
        for reading in body["readings"]:
            reading_data = plug_data.copy()
            reading_data.update(reading)
            tasks.append(client.post(DATABASE_URL + "/internal-temp", json=reading_data))
        
        # RUN ALL TASKS
        responses = await asyncio.gather(*tasks, return_exceptions=False)
        
        # CHECK STATUS CODES
        for res in responses:
            if res.status_code != 201:
                return (NoContent, res.status_code)
    
    # RETURN
    return (NoContent, 201)


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)