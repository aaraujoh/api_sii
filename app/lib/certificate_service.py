
"""

 1- Load certificate
 2- Sign

"""

import sys
import logging
import subprocess
import os
from instance.config import OPENSSL_PATH, APP_PATH
# from lib.models.dte import DTECAF
# from lib.models.database.db_caf import CAF
# from lib.models.database.context import Session

DUMMY_PASSWORD="Kaka100"
class CertificateService:
	""" Properties """
	certificate = None
	key = None
	_pfx_password = ''
	_pfx_path = ''

	key_path = APP_PATH + r'\cert\keyfile.key'
	cert_path = APP_PATH + r'\cert\certificate.crt'
	sii_cert_path = APP_PATH + r'\cert\sii_public.cert'
	#@@
	key_path = APP_PATH + r'/cert/keyfile.key'
	cert_path = APP_PATH + r'/cert/certificate.crt'
	sii_cert_path = APP_PATH + r'/cert/sii_public.cert'


	def __init__(self, pfx_file_path, pfx_password=''):
		self._pfx_password = pfx_password
		self._pfx_path = pfx_file_path

	def generate_certificate_and_key(self):
		""" Generar certificado y clave """
		""" Get logger """
		logger = logging.getLogger()
		logger.info("set_certificate::Loading certificate from " + str(self._pfx_path))

		#  openssl pkcs12 -in ../../client_ssl.pem -passin pass:2022  -passout pass:2022 -export -out bob_pfx.pfx
		subprocess.run(
			[OPENSSL_PATH, "pkcs12", "-in", self._pfx_path ,
			 "-passin", "pass:" + self._pfx_password, "-passout", "pass:" + DUMMY_PASSWORD, # self._pfx_password,
			 "-export",
			 "-out", self._pfx_path + ".pfx"])
		""" Generate encrypted privated key """

		#subprocess.run([OPENSSL_PATH, "pkcs12", "-in", self._pfx_path + ".pfx","-passin", "pass:" +self._pfx_password, "-passout","pass:" +self._pfx_password, "-out", self.key_path])
		subprocess.run([OPENSSL_PATH, "pkcs12", "-in", self._pfx_path + ".pfx", "-passin", "pass:" + DUMMY_PASSWORD,  "-passout", "pass:" + DUMMY_PASSWORD, "-out", self.key_path])
		""" Get certificate """
		#subprocess.run([OPENSSL_PATH, "pkcs12", "-in", self._pfx_path+ ".pfx", "-clcerts", "-nokeys", "-passin", "pass:" +self._pfx_password, "-passout","pass:" + self._pfx_password, "-out", self.cert_path])
		subprocess.run([OPENSSL_PATH, "pkcs12", "-in", self._pfx_path + ".pfx", "-clcerts", "-nokeys", "-passin","pass:" + DUMMY_PASSWORD, "-passout", "pass:" + DUMMY_PASSWORD, "-out", self.cert_path])

		""" Decrypte private key """
		#subprocess.run([OPENSSL_PATH, "rsa", "-in", self.key_path + ".pfx", "-passin", "pass:" +self._pfx_password, "-passout","pass:" +self._pfx_password, "-out", self.key_path])
		subprocess.run([OPENSSL_PATH, "rsa", "-in", self.key_path + ".pfx", "-passin", "pass:" + DUMMY_PASSWORD, "-passout","pass:" + DUMMY_PASSWORD, "-out", self.key_path])
		""" Load temporary created files and delete """
		self._load_certficate_and_key()
		self._remove_certificate_and_key()

	def read_file(self, f_name):
		with open(f_name, "rb") as f:
			return f.read()

	def _load_certficate_and_key(self):
		""" Cargamos en memoria el certificado y la clave """
		self.certificate = self.read_file(self.cert_path)
		self.key = self.read_file(self.key_path)

	def _remove_certificate_and_key(self):
		""" Eliminamos los archivos temporales """
		try:
			os.remove(self.key_path)
		except OSError as e:  ## if failed, report it back to the user ##
			print ("Error: %s - %s." % (e.filename, e.strerror))
		try:
			os.remove(self.cert_path)
		except OSError as e:  ## if failed, report it back to the user ##
			print ("Error: %s - %s." % (e.filename, e.strerror))

	def get_password(self):
		return self._pfx_password
