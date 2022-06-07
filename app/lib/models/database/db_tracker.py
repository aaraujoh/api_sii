import datetime
from sqlalchemy import *
from lib.models.database.base import Base
from lib.models.database.db_document import Document
from lib.models.database.abs_owned import Owned
from sqlalchemy.orm import relationship


class Tracker(Base, Owned):
	__tablename__ = 'DTE_Tracker'
	id = Column(Integer, primary_key=True)
	serial = Column(String)
	sent_date = Column(DateTime, default=datetime.datetime.utcnow)
	document_id = Column(Integer, ForeignKey(Document.id))
	state = Column(Integer)
	result = Column(String)

	""" Navigation property """
	document = relationship("Document", lazy="joined")