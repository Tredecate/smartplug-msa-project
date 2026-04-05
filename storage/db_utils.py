import functools

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import Base
from config_handler import APP_CONFIG


# ENGINE SETUP
ENGINE = create_engine(
        f"{APP_CONFIG['db']['protocol']}://{APP_CONFIG['db']['username']}:{APP_CONFIG['db']['password']}@{APP_CONFIG['db']['host']}/{APP_CONFIG['db']['database']}",
        pool_recycle=APP_CONFIG['db']['pool_recycle_interval_secs']
    )


# BASIC FETCHERS
def get_engine():
    return ENGINE

def make_session():
    return sessionmaker(bind=ENGINE)()


# TABLE MANAGEMENT
def drop_all_tables():
    Base.metadata.drop_all(ENGINE)
    return True

def create_all_tables():
    Base.metadata.create_all(ENGINE)
    return True


# DB SESSION DECORATOR
def use_db_session(func):
    @functools.wraps(func)

    def wrapper(*args, **kwargs):
        session = make_session()
        try:
            return func(session, *args, **kwargs)
        finally:
            session.close()

    return wrapper


# IF RUN AS SCRIPT
if __name__ == "__main__":
    from sys import argv

    if not any(valid_args in argv for valid_args in ['drop', 'create', 'reset']):
        print("Please provide an argument: 'drop', 'create', or 'reset'")
        print("  'drop'   - drops all tables")
        print("  'create' - creates all tables")
        print("  'reset'  - drops and then creates all tables")
        print("Example: python db_utils.py reset")
        exit(1)
    
    if 'drop' in argv or 'reset' in argv:
        drop_all_tables()
        print("Dropped all tables.")

    if 'create' in argv or 'reset' in argv:
        create_all_tables()
        print("Created all tables.")
        
    exit(0)