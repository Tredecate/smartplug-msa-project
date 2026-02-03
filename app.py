import connexion
from connexion import NoContent

from db_utils import use_db_session
from models import EnergyConsumedReading, InternalTempReading
from config_handler import APP_CONFIG, API_CONFIG


@use_db_session
def store_energy_consumption_reading(session, body: dict) -> tuple[object, int]:
    reading = EnergyConsumedReading(**body) # Unpacking lesgoooo

    session.add(reading)
    session.commit()

    return (NoContent, 201)


@use_db_session
def store_internal_temp_reading(session, body: dict) -> tuple[object, int]:
    reading = InternalTempReading(**body)

    session.add(reading)
    session.commit()

    return (NoContent, 201)


# SETUP CONNEXION APP
app = connexion.FlaskApp(__name__, specification_dir=API_CONFIG["spec_dir"])
app.add_api(API_CONFIG["file"], 
            strict_validation=API_CONFIG["strict_validation"], 
            validate_responses=API_CONFIG["validate_responses"])


# GO GO GO
if __name__ == "__main__":
    if APP_CONFIG["auto_create_tables"]:
        from db_utils import create_all_tables
        create_all_tables() # metadata.create_all() checks first by default, so this SHOULD be safe
    
    app.run(port=APP_CONFIG["port"])