from zeep import Plugin
from lxml import etree
import xmlsec
import base64
import logging

CHECK_XML_SCHEMA = True
DUMMY_PASSWORD="Kaka100"
class SiiPlugin(Plugin):
	key = ''
	cert = ''
	SIGNATURE_TAG = '{{SIGNATURE}}'
	URI_TAG = '{{URI}}'
	NODE_ID_ATTR = 'ID'

	""" Override """
	def ingress(self, envelope, http_headers, operation):
		""" Hook on received messages """
		return envelope, http_headers

	""" Override """
	def egress(self, envelope, http_headers, operation, binding_options):
		""" Hook on sent messages to override behavior if needed """
		if("getToken" == operation.name):
			print(str(operation.name))
		elif("getSemilla" in operation.name):
			print(str(operation.name))
		else:
			print(str(operation.name))

		return envelope, http_headers

	__replace_char = {'&' : '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', '\'': '&apos;'}
	def sanitize_data(self, input_data:str) -> str:
		""" Remplaza algunos caracteres no autorizados en el XML """
		clean_data = ''
		for k in self.__replace_char:
			clean_data = input_data.replace(k, self.__replace_char[k])

		return clean_data

	def read_file(self, f_name:str='cert/sign_sii_xml.tmpl'):
		with open(f_name, "rb") as f:
			return f.read()

	def verify(self, message_with_template_included:str, node_type_name:str=''):
		""" Verificar firma """
		logger = logging.getLogger()
		logger.info("SiiPlugin::verify Verifying element with template.")
		"""Should sign a file using a dynamicaly created template, key from PEM and an X509 cert."""
		assert(message_with_template_included)
		# Load the pre-constructed XML template.
		template = etree.fromstring(message_with_template_included)

		# Find the last <Signature/> node.
		signature_node = template.findall('{http://www.w3.org/2000/09/xmldsig#}Signature')[-1]

		assert signature_node is not None
		assert signature_node.tag.endswith(xmlsec.Node.SIGNATURE)

		print("Verify " + node_type_name)
		ctx = xmlsec.SignatureContext()

		if len(node_type_name) > 0:
			""" Agregamos el tipo de nodo y su referencia al contexto """
			reference_node = template.find(node_type_name)
			ctx.register_id(node=reference_node, id_attr=self.NODE_ID_ATTR)
		try:
			# @@HARDCODE
			ctx.key = xmlsec.Key.from_memory(self.key, format=xmlsec.constants.KeyDataFormatPem, password=DUMMY_PASSWORD)
			ctx.key.load_cert_from_memory(self.cert, format=xmlsec.constants.KeyDataFormatCertPem)
		except xmlsec.Error as e:
			logger.error("SiiPlugin::sign Key or certificate could not be loaded.")
			print(str(e))
			return ''

		ctx.verify(signature_node)

	def sign_tagged_message(self, tagged_message:str, doc_node:str="{http://www.sii.cl/SiiDte}Documento", det_node:str="{http://www.sii.cl/SiiDte}DTE", set_node:str="{http://www.sii.cl/SiiDte}SetDTE") -> str:
		""" Firma un documento que contiene los marcadores necesarios para ser remplazados
			por templates de firma """
		DOCUMENT_NODE = doc_node
		DET_NODE = det_node
		SET_NODE = set_node
		full_message = etree.fromstring(tagged_message)

		""" Obtener los nudos dtes """
		dtes = [d for d in full_message.iter(DET_NODE)]

		if len(dtes) == 0:
			raise ValueError("No se encontró DTE para firmar")

		""" Firma individual para cada documento """
		for child in dtes:
			""" Sign child """
			document = etree.tostring(child, pretty_print=False).decode('ISO-8859-1')
			""" Buscamos el Documento y su Id """
			document_id = child.find(DOCUMENT_NODE).get(self.NODE_ID_ATTR)
			print(DOCUMENT_NODE)
			if len(document_id) > 0:
				""" Remplazamos la referencia con el código del documento """
				document = document.replace(self.URI_TAG, document_id)
				""" Firma + Verificación """
				signed_document = self.sign(document, DOCUMENT_NODE)
				self.verify(signed_document, DOCUMENT_NODE)
				""" Find parent and insert signed child, remove old one """
				parent = child.find("..")
				parent.remove(child)
				parent.append(etree.fromstring(signed_document))
				""" DEBUG : Prueba con https://www.aleksey.com/xmlsec/xmldsig-verifier.html """
				if False:
					""" Agregar encabezado especifico """
					DEBUG_XML_SIG_HEADER = "<?xml version='1.0' encoding='ISO-8859-1'?>" + \
											"<!DOCTYPE DTE [" + \
											"<!ATTLIST Documento ID ID #IMPLIED>" + \
											"]>"

					doc_path = 'temp/DTE_ENV_node_' + document_id + '.xml'
					myXML = open(doc_path, "w")
					signed_document = DEBUG_XML_SIG_HEADER + signed_document
					myXML.write(signed_document)

		""" Firma global para el envio """
		""" Actualizamos el full message """
		tagged_message = etree.tostring(full_message, pretty_print=False).decode('ISO-8859-1')

		""" Buscamos el Documento y su Id """
		set_node = full_message.find(SET_NODE)
		set_id = set_node.get(self.NODE_ID_ATTR)

		if len(set_id) > 0:
			""" Remplazamos la referencia con el código del set """
			tagged_message = tagged_message.replace(self.URI_TAG, set_id)
			""" Firma + Verificación """
			signed_document = self.sign(tagged_message, SET_NODE)
			self.verify(signed_document, SET_NODE)

		""" Validamos el esquema XML """
		if CHECK_XML_SCHEMA:
			validation = self.validate_XML(signed_document, 'lib/models/schema_dte/EnvioDTE_v10.xsd')
			if not validation:
				raise ValueError("Error al validar el esquema XML")

		""" Esa linea me da verguenza, perdon """
		""" Restablecemos el XMLNS tal como fue firmado """
		signed_document = signed_document.replace('<DTE version="1.0">', '<DTE xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1.0">')
		return signed_document

	def validate_XML(self, xml_content: str, xsd_path: str) -> bool:
		""" Realiza la validación de un XML con su esquema XSD """
		xmlschema_doc = etree.parse(xsd_path)
		xmlschema = etree.XMLSchema(xmlschema_doc)

		xml_doc = etree.fromstring(xml_content)
		result = xmlschema.validate(xml_doc)

		try:
			xmlschema.assertValid(xml_doc)
		except etree.DocumentInvalid as xml_errors:
			print("List of errors:\r\n" + str(xml_errors.error_log))
			pass

		return result

	def sign(self, message_with_template_included:str, node_type_name:str='') -> str:
		""" Firma un string con template xmldsig Signature incorporado """
		logger = logging.getLogger()
		logger.info("SiiPlugin::sign Signing element with template.")
		assert(message_with_template_included)

		template = etree.fromstring(message_with_template_included)

		signature_node = template.findall('{http://www.w3.org/2000/09/xmldsig#}Signature')[-1]

		assert signature_node is not None
		assert signature_node.tag.endswith(xmlsec.Node.SIGNATURE)

		print("Sign " + node_type_name)
		ctx = xmlsec.SignatureContext()

		if len(node_type_name) > 0:
			""" Agregamos el tipo de nodo y su referencia al contexto """
			reference_node = template.find(node_type_name)
			if reference_node is not None:
				print(reference_node)
				ctx.register_id(node=reference_node, id_attr=self.NODE_ID_ATTR)
			else:
				raise ValueError("No se encontró ningun nodo de tipo " + node_type_name)

		try:
			# @@@HARDCOE
			ctx.key = xmlsec.Key.from_memory(self.key, format=xmlsec.constants.KeyDataFormatPem, password=DUMMY_PASSWORD)
			ctx.key.load_cert_from_memory(self.cert, format=xmlsec.constants.KeyDataFormatCertPem)
		except xmlsec.Error as e:
			logger.error("SiiPlugin::sign Key or certificate could not be loaded.")
			print(str(e))
			return ''

		ctx.sign(signature_node)
		return etree.tostring(template, pretty_print=False).decode('ISO-8859-1')
