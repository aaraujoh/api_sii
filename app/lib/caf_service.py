"""
	Manage CAF (Código de Autorización de Folios, Docuemnt authorization code)
"""
from typing import List, Dict
from sqlalchemy import func, and_, or_
from lib.models.dte import DTECAF
from lib.models.database.db_caf import CAF
from lib.models.database.context import Session

class CAFService:
	_user_id = -1
	def __init__(self, user_id:int):
		self._user_id = user_id

	def get_next_document_number_by_type(self, document_type:int) -> (int, int):
		""" Buscamos el CAF vigente correpsondiente al tipo de documento y devolvemos el ultimo folio """
		caf = self.get_caf_for_document_type(document_type)
		return self.get_next_document_number(caf.id), caf.id

	def get_next_document_number(self, caf_id:int) -> int:
		""" Read from storage and return next code """
		with Session() as db_context:
			result:CAF = db_context.query(CAF).filter(and_(CAF.user_id == self._user_id, CAF.id == caf_id)).scalar()
			""" Ya se ocuparon algunos correlativos """
			if result.last_number_used:
				""" Devolvemos el siguiente """
				result.last_number_used = result.last_number_used + 1
				if result.last_number_used >= result.document_number_to:
					""" Se trata del ultimo correlativo del rango, dejamos el CAF como "Terminado" """
					result.last_number_used = result.document_number_to
					result.state = 0
			else:
				""" Primer correlativo del rango del CAF """
				result.last_number_used = result.document_number_from

			db_context.commit()

			return result.last_number_used

	def import_from_XML(self, xml_content):
		""" Importa un CAF desde un XML y lo alamacena en BDD, asociado al usuario """
		caf = DTECAF(parameters={}, signature='', private_key='')
		caf.load_from_XML_string(xml_content)
		with Session() as db_context:
			db_caf = CAF()
			db_caf.document_type = caf.get_document_type()
			db_caf.document_number_from = int(caf.get_caf_property("Range")['From'])
			db_caf.document_number_to = int(caf.get_caf_property("Range")['Hasta'])
			db_caf.file = xml_content.decode()
			db_caf.state = 1
			db_caf.user_id = self._user_id
			""" Ultimo folio utilizado es el "Desde" - 1 """
			db_caf.last_number_used = db_caf.document_number_from - 1
			db_context.add(db_caf)
			db_context.commit()

	def get_created_CAF(self) -> List[CAF]:
		""" Devuelve todos los CAF asociados al usuario """
		with Session() as db_context:
			result = db_context.query(CAF).filter(CAF.user_id == self._user_id).all()
			return result

	def get_caf_for_document_type(self, document_type:int) -> CAF:
		""" Busca un documento CAF valido para este tipo de documento y lo devuelve o raise FileNotFoundError """
		with Session() as db_context:
			result = db_context.query(CAF).filter(and_(CAF.user_id == self._user_id, CAF.document_type == document_type, CAF.state == 1)).scalar()
			if not result:
				raise FileNotFoundError("No se encontró ningún archivo CAF valido para este tipo de documento.")
			return result

