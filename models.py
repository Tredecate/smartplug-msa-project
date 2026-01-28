from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, mapped_column
from sqlalchemy import Integer, Float, String, DateTime, Uuid, TypeDecorator, func


class Base(DeclarativeBase):
    pass


# TYPE CONVERSION DECORATORS
class ISODateTime(TypeDecorator):
    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if isinstance(value, str):
            return datetime.fromisoformat(value)
        return value



# TEMPLATE CLASS FOR COMMON COLUMNS
class ReadingBase:
    id =                mapped_column(Integer,              primary_key=True, autoincrement=True)
    plug_id =           mapped_column(Uuid(as_uuid=False),  nullable=False)

    plug_country =      mapped_column(String,   nullable=True)
    plug_uptime =       mapped_column(Integer,  nullable=False)
    
    reading_timestamp = mapped_column(ISODateTime(timezone=True),   nullable=False)
    batch_timestamp =   mapped_column(ISODateTime(timezone=True),   nullable=False)
    date_created =      mapped_column(DateTime(timezone=True),      nullable=False, server_default=func.now())


# SPECIFIC TABLE CLASSES
class EnergyConsumedReading(Base, ReadingBase):
    __tablename__ = "energy_consumed_reading"
    
    energy_consumed_watt_minutes =  mapped_column(Integer,  nullable=False)
    switch_state =                  mapped_column(String,   nullable=False)

class InternalTempReading(Base, ReadingBase):
    __tablename__ = "internal_temperature_reading"
    
    internal_temp_celsius = mapped_column(Float,    nullable=False)
    thermal_status =        mapped_column(String,   nullable=False)