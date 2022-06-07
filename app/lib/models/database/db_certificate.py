import datetime
from sqlalchemy import *
from lib.models.database.base import Base
from lib.models.database.db_document import Document
from lib.models.database.abs_owned import Owned
from sqlalchemy.orm import relationship

class Certificate(Base, Owned):
	__tablename__ = 'DTE_Certificate'
	id = Column(Integer, primary_key=True)
	serial = Column(String)
	upload_date = Column(DateTime, default=datetime.datetime.utcnow)
	file = Column(LargeBinary)
	state = Column(Integer)