from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

def initialize_database(url:str="sqlite:///patrol_scheduler.db"):
    engine=create_engine(url); Base.metadata.create_all(engine); return sessionmaker(engine)
