import datetime
from sqlalchemy import *
from lib.models.database.base import Base
from lib.models.database.abs_owned import Owned
from sqlalchemy.orm import relationship

class CAF(Base, Owned):
	__tablename__ = 'DTE_CAF'
	id = Column(Integer, primary_key=True)
	document_type = Column(Integer)
	""" String not BLOB, ton store charset """
	file = Column(String)
	document_number_from = Column(Integer)
	document_number_to = Column(Integer)
	upload_date = Column(DateTime, default=datetime.datetime.utcnow)
	last_number_used = Column(Integer, default=0)
	state = Column(Integer)