from instance.config import SQL_ALCHEMY_DATABASE_URI, SQL_ALCHEMY_DATABASE_OPTION
from sqlalchemy import create_engine, Sequence, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm.session import close_all_sessions
from sqlalchemy.schema import CreateSequence
from sqlalchemy.event import listens_for

from lib.models.database.base import Base
from lib.models.database.db_users import User

from lib.models.database.db_caf import CAF
from lib.models.database.db_document import Document
from lib.models.database.db_tracker import Tracker
from lib.models.database.db_certificate import Certificate

Session = sessionmaker()

def initialize_db():
	""" Production database """
	#engine = create_engine(SQL_ALCHEMY_DATABASE_URI, pool_size=50, connect_args=SQL_ALCHEMY_DATABASE_OPTION)
	engine = create_engine(SQL_ALCHEMY_DATABASE_URI)
	Session.configure(bind=engine)
	""" Establish first connection """
	engine.connect()
	print(" * [SA] Dialect : " + str(engine.url.get_dialect().name))

"""
For MSSQL to avoid lock, this should be executed:
ALTER DATABASE MyDatabase SET ALLOW_SNAPSHOT_ISOLATION ON;
ALTER DATABASE MyDatabase SET READ_COMMITTED_SNAPSHOT ON;
"""
def create_production_database():
	print("* /_!_\ Inicialización de base de datos")
	print("* Ubicación: " + str(SQL_ALCHEMY_DATABASE_URI) + " opción: " + str(SQL_ALCHEMY_DATABASE_OPTION))
	continue_value = input("Este procedimiento va a borrar TODOS los datos de la base mencionada y volver a crearla, seguro desea seguir ? (s/n)")

	""" Establish first connection """
	engine = create_engine(SQL_ALCHEMY_DATABASE_URI)#, pool_size=50, connect_args=SQL_ALCHEMY_DATABASE_OPTION)
	Session.configure(bind=engine)
	engine.connect()
	if continue_value == 's':
		with Session() as session:
			print(" * [SA] /_!_\ DROPPING DATABASE")
			Base.metadata.drop_all(engine)
			print(" * [SA] /_!_\ CREATING DATABASE")
			Base.metadata.create_all(engine)
			session.commit()
			print(" * [SA] Database created succesfully")
		print(" * [SA] Dialect : " + str(engine.url.get_dialect().name))