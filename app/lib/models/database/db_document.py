from sqlalchemy import *
from lib.models.database.base import Base
from lib.models.database.db_caf import CAF
from lib.models.database.abs_owned import Owned
from sqlalchemy.orm import relationship

class Document(Base, Owned):
	__tablename__ = 'DTE_Document'
	id = Column(Integer, primary_key=True)
	document_number = Column(Integer)
	document_code = Column(String)
	document_type = Column(Integer)
	json_string = Column(String)
	xml_string = Column(String)
	pdf_file = Column(BLOB)
	#pdf_file = Column(String)
	caf_id = Column(Integer, ForeignKey(CAF.id))