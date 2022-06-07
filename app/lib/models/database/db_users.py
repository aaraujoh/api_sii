from sqlalchemy import *
from lib.models.database.base import Base
from sqlalchemy.orm import relationship

class User(Base):
    __tablename__ = 'DTE_User'
    id = Column(Integer, primary_key=True)
    rut = Column(String)
    name = Column(String)
    hashed_pass = Column(String)
    api_key = Column(String)