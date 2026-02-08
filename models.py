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
class ReadingBase(Base):
    __abstract__ = True

    id =                mapped_column(Integer,              primary_key=True, autoincrement=True)
    plug_id =           mapped_column(Uuid(as_uuid=False),  nullable=False)

    plug_country =      mapped_column(String(2),   nullable=True)
    plug_uptime =       mapped_column(Integer,  nullable=False)
    
    reading_timestamp = mapped_column(ISODateTime(timezone=True),   nullable=False)
    batch_timestamp =   mapped_column(ISODateTime(timezone=True),   nullable=False)
    batch_trace_id =    mapped_column(Uuid(as_uuid=False),          nullable=False)
    date_created =      mapped_column(DateTime(timezone=True),      nullable=False, server_default=func.now())

    def as_dict(self):
        return {column.name: getattr(self, column.name) for column in self.__table__.columns if column.name != "id"}


# SPECIFIC TABLE CLASSES
class EnergyConsumedReading(ReadingBase):
    __tablename__ = "energy_consumed_reading"
    
    energy_consumed_watt_minutes =  mapped_column(Integer,  nullable=False)
    switch_state =                  mapped_column(String(3),   nullable=False)

class InternalTempReading(ReadingBase):
    __tablename__ = "internal_temperature_reading"
    
    internal_temp_celsius = mapped_column(Float,    nullable=False)
    thermal_status =        mapped_column(String(13),   nullable=False)