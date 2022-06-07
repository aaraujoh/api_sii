import requests
import re
import datetime
import logging
from lib.models.database.db_tracker import Tracker
# from lib.models.database.context import Session


SII_CERTIFICATION_ENV = 'https://maullin.sii.cl'
SII_PRODUCTION_ENV = 'https://palena.sii.cl'

def _get_re_match(re_expression:str, text:str) -> str:
	result = ''
	match = re.search(re_expression, text, re.MULTILINE)
	if match:
		result = match.group(1)
	return result

class SiiDocumentUploader():
	""" State seems to be at least 3 digits """
	REGEX_MATCH_STATE = r"<STATUS>(\d{1,})</STATUS>"
	REGEX_MATCH_TRACKID = r"<TRACKID>(.*)</TRACKID>"
	_token = ''
	_url = ''
	_application_name = ''
	_referer = ''
	_user_id = -1

	def __init__(self, token:str, url:str=SII_CERTIFICATION_ENV+'/cgi_dte/UPL/DTEUpload', application_name:str='sii-dte-py', referer:str='https://daia.cl', user_id:int=-1):
		self._token = token
		self._url = url
		self._application_name = application_name
		self._referer = referer
		self._user_id = user_id

	def send_document(self, user_rut:str, company_rut:str, document_path:str, doc_id:str, document_content:str=None):
		""" Realiza el envío 'POST' del archivo firmado """
		logger = logging.getLogger()
		if document_path:
			with open(document_path, 'r', encoding='ISO-8859-1') as myXML:
				document_content = myXML.read()
				document_content = document_content.encode('ISO-8859-1')

		payload = { \
			'rutSender': user_rut.split('-')[0], \
			'dvSender': user_rut.split('-')[1], \
			'rutCompany': company_rut.split('-')[0], \
			'dvCompany': company_rut.split('-')[1]
		}

		headers = { \
				'User-Agent': 'Mozilla/4.0 (compatible; PROG 1.0; ' + self._application_name + ')', \
				'Referer': self._referer, \
				'Cookie': 'TOKEN=' + self._token
		}

		file = 	{'archivo': (str(doc_id) + '.xml', document_content, 'text/xml')}

		r = requests.post(self._url, data=payload, files=file, headers=headers)

		""" Generamos un objeto de resultado """
		try:
			result = self.parse_response(r.text)
			result['user_rut'] = user_rut
			result['company_rut'] = company_rut
			result['doc_id'] = doc_id
			result['token'] = self._token
		except Exception as e:
			""" Re throw """
			logger.error("send_document:: '" + str(e) + "' for user " + str(self._user_id))
			logger.error("send_document:: Result " + str(result))
			raise e

		return result

	def parse_response(self, response_text:str):
		""" Implementación del parse de la respuesta """
		result = {}
		result['status'] = response_text
		status_code = -1
		track_id = ''
		""" Extraer el estado """
		status_code = _get_re_match(self.REGEX_MATCH_STATE, response_text)

		""" El status tiene que ser un digito """
		status_code = int(status_code)
		if status_code == 0:
			""" OK, recibido, extraer el trackID """
			result['status'] = int(status_code)

			""" Extraer el trackID """
			track_id = _get_re_match(self.REGEX_MATCH_TRACKID, response_text)
			result['track_id'] = track_id
		elif status_code == 1:
			raise ValueError("El usuario no tiene permiso para enviar.")
		elif status_code == 6:
			raise ValueError("La empresa no tiene permiso para enviar.")
		elif status_code == 8:
			raise ValueError("Error en la firma del archivo")

		return result

if __name__ == '__main__':
	test = '<?xml version="1.0"?>' + \
			'<RECEPCIONDTE>' + \
				'<RUTSENDER>25656563-3</RUTSENDER>' + \
				'<RUTCOMPANY>77368325-5</RUTCOMPANY>' + \
				'<FILE>envio.xml</FILE>' + \
				'<TIMESTAMP>2022-01-05 15:33:06</TIMESTAMP>' + \
				'<STATUS>0</STATUS>' + \
				'<TRACKID>0150400582</TRACKID>' + \
			'</RECEPCIONDTE>'

	sii_du = SiiDocumentUploader('test')
	response = sii_du.parse_response(test)
	print(response)