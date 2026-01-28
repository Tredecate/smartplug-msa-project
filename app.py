import connexion
from connexion import NoContent

from db_utils import use_db_session
from models import EnergyConsumedReading, InternalTempReading


AUTO_CREATE_TABLES = True


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


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    if AUTO_CREATE_TABLES:
        from db_utils import create_all_tables
        create_all_tables() # metadata.create_all() checks first by default, so this SHOULD be safe
    
    app.run(port=8090)