import sys
import logging
import subprocess
import os
import datetime

from sqlalchemy import func, and_, or_
from lib.models.database.db_caf import CAF
from lib.models.database.db_tracker import Tracker
from lib.models.database.db_document import Document
from lib.models.database.context import Session

class DocumentService:
	_user_id = -1
	_states = {
		1: "EN ESPERA",
		2: "ENVIANDO",
		3: "ENVIADO",
		99: "EN ERROR"
		}

	def __init__(self, user_id:int):
		self._user_id = user_id

	def get_document(self, document_id:int) -> Document:
		""" Obtener document con id """
		with Session() as db_context:
			return db_context.query(Document).filter(and_(Document.id == document_id, Document.user_id == self._user_id)).one_or_none()

	def get_document_by_code(self, document_code:str) -> Document:
		""" Obtener document con code """
		with Session() as db_context:
			return db_context.query(Document).filter(and_(Document.document_code == document_code, Document.user_id == self._user_id)).one_or_none()

	def save_document(self, caf_id:int, document_number:int, document_code:str, document_type:int, document_xml:str, document_json:str, pdf_file:bytes=b'', state:int=1) -> int:
		""" Guardamos el documento especificado et retornamos el id """
		with Session() as db_context:
			""" Revisamos si ya existe el documento (folio, tipo, usuario), de ser as�, exception """
			if document_number > 0:
				already_exists = db_context.query(Document).filter(and_(Document.document_number == document_number,\
																		Document.document_code == document_code,\
																		Document.document_type == document_type,\
																		Document.user_id == self._user_id)).one_or_none()
			else:
				already_exists = db_context.query(Document).filter(and_(Document.document_code == document_code,\
																		Document.document_type == document_type,\
																		Document.user_id == self._user_id)).one_or_none()
			if already_exists:
				raise KeyError("El documento con este id ya fue creado.")
			else:
				""" Lo creamos """
				document = Document()
				document.user_id = self._user_id 
				document.document_number = document_number
				document.document_code = document_code.replace(' ', '')
				document.document_type = document_type
				document.xml_string = document_xml
				document.json_string = document_json
				document.pdf_file = pdf_file
				if caf_id and caf_id > 0:
					""" Revisamos si existe el CAF y si el numero de documento est� en su rango """
					""" En caso de CAF ID = 0, el CAF fue entregado por un servicio externo """
					caf:CAF = db_context.query(CAF).filter(and_(CAF.user_id == self._user_id,
														CAF.id == caf_id )).one_or_none()
					""" Controlamos la integridad de los datos """
					if not caf:
						raise KeyError("El CAF referenciado no existe.")
					if caf.document_type != int(document_type):
						raise ValueError("El CAF referenciado corresponde a otro tipo de documento.")
					if document_number > caf.document_number_to or document_number < caf.document_number_from:
						raise ValueError("El n�mero de folio no est� dentro del rango del CAF referenciado.")
					if document_number > caf.last_number_used:
						raise ValueError("El n�mero de folio es mayor al �ltimo numero utilizado del CAF referenciado.")

					document.caf_id = caf_id
				db_context.add(document)
				db_context.commit()

				""" Creamos un tracker para registrar su estado """
				tracker = Tracker()
				tracker.document_id = document.id
				tracker.user_id = self._user_id
				tracker.state = state
				db_context.add(tracker)
				db_context.commit()

				return document.id

	def update_document(self, document_id:int, document_xml:str='', document_json:str='', pdf_file:bytes=b''):
		""" Actualizar un documento guardado """
		with Session() as db_context:
			document:Document = db_context.query(Document).filter(Document.id == document_id).scalar()
			if len(document_xml) > 0:
				document.xml_string = document_xml
			if len(document_json) > 0:
				document.json_string = document_json
			if len(pdf_file) > 0:
				document.pdf_file = pdf_file
			db_context.commit()

	def reset_pdf(self, document_id:int):
		""" Resetear el archivo PDF guardado con un documento """
		with Session() as db_context:
			document:Document = db_context.query(Document).filter(Document.id == document_id).scalar()
			document.pdf_file = None
			db_context.commit()


	def set_document_state(self, document_id:int, state:int, serial:str='', result:str='') -> int:
		""" Actualizamos el tracker del documento referenciado """
		with Session() as db_context:
			tracker:Tracker = db_context.query(Tracker).filter(and_(Tracker.document_id == document_id, Tracker.user_id == self._user_id)).one_or_none()

			if not tracker:
				raise KeyError("El tracker con este id no existe.")
			else:
				tracker.state = state
				""" Actualizamos la fecha de cambio de estado """
				tracker.sent_date = datetime.datetime.now()
				tracker.serial = serial
				tracker.result = result
				db_context.commit()

				return tracker.id