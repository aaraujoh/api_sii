import tempfile

import logging
import sys
import json


from lxml import etree
from lib.models.sii_token import Token
from lib.zeep.sii_plugin import SiiPlugin
from lib.models.dte import DTECAF, DTEBuidler, DTECover, DTEPayload, DTEPerson
from lib.models.ack_dte import DTEAck, DTEComAck
from lib.sii_connector_auth import SiiConnectorAuth
from lib.certificate_service import CertificateService
from lib.sii_document_uploader import SiiDocumentUploader
from lib.pdf_generator import PDFGenerator


logger = logging.getLogger()
logging.basicConfig(level=logging.INFO)



# params = {
#     "caf":"",
#     "discounts":{},
#     "items":{},
#     "receiver":{},
#     "references":{},
#     "sender":{},
#     "specifics":{},
#     "user":{},
#     "type": 12,
#     "config": {
#         "pem":"",
#         "pem_pass":""
#     }
# }

def upload_xml(params):
    import ssl
    logger.info(ssl.OPENSSL_VERSION)
    # pdf = PDFGenerator()
    envelope = {}
    """ Dump test XML """

    document_count = None #len(sys.argv) == 6 and int(sys.argv[5])

    if not document_count:
        document_count = 1

    for i in range(1, document_count + 1):
        sender_parameters = {}
        receiver_parameters = {}
        specific_header_parameters = {}
        item_list = {}
        path = 'test/data_' + str(i)
        """ Read test files """
        user_parameters = params["user"]
        sender_parameters = params["sender"]
        receiver_parameters = params["receiver"]
        item_list = params["items"]
        reference_list = params["references"]
        specific_header_parameters = params["specifics"]
        discounts_parameters = params["discounts"]

        caf = DTECAF(parameters={}, signature='', private_key='')
        caf.load_from_XML_string( params["caf"])

        builder = DTEBuidler()

        """ Bind user information, mocked for this process """
        specific_header_parameters['User'] = {}
        specific_header_parameters['User']['Resolution'] = params["resolution_number"]
        specific_header_parameters['User']['ResolutionDate'] = params["resolution_date"]
        specific_header_parameters['User']['RUT'] = user_parameters['RUT']

        documents = builder.build(params["type"], sender_parameters, receiver_parameters, specific_header_parameters,
                                  item_list, reference_list, discounts_parameters, caf)
        """ Primer documento generado """
        _, pretty_dte, dte_object = documents
        logger.info(f"DTE_OBJECT {str(dte_object.dump())}")
        ###@@@pdf = PDFGenerator()
        ###@@@pdf.generate(dte_object)
        """ Add to envelope to be send """
        envelope[i] = dte_object
        if i < document_count:
            print("Cargar documento siguiente ?")
            resp = input()
    # raise ValueError("STOP")
    """ Generate cover (Caratula) """
    cover = DTECover(dtes=envelope, resolution={'Date': params["resolution_date"], 'Number': params["resolution_number"]}, user=user_parameters)

    """ Generate payload to be uploaded (without signature, only tagged) """
    payload = DTEPayload(dtes=envelope, cover=cover, user={}, set_id="Set" + str(params["type"]) + "-" + str(document_count))
    siiSignature = SiiPlugin()

    """ Load key """
    result = {}
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix="pem_", dir="temp") as fd:
        fd.write(params["config"]["pem"])
        fd.flush()
        cert = CertificateService(pfx_file_path=fd.name, pfx_password=params["config"]["pem_pass"])
        cert.generate_certificate_and_key()
        siiSignature.key = cert.key
        siiSignature.cert = cert.certificate

        """ Remove declaration """
        declare = '<?xml version="1.0" encoding="ISO-8859-1"?>'
        payload = payload.dump_without_xml_declaration()

        """ Sign """
        ready_to_upload = siiSignature.sign_tagged_message(payload)

        """ Add declaration back """
        ready_to_upload = declare + '\n' + ready_to_upload

        """ Write ready-to-upload XML  (without signature) """
        doc_path = 'temp/DTE_ENV' + str(dte_object.get_document_id()) + '_ru.xml'
        myXML = open(doc_path, "w", encoding="ISO-8859-1")
        myXML.write(ready_to_upload)
        logger.info(f"PAYLOAD	 {str(ready_to_upload)}")
        """ Get token """
        auth = SiiConnectorAuth(module=SiiConnectorAuth.GET_SEED_MODULE_ID)
        seed = auth.get_seed()
        auth = SiiConnectorAuth(module=SiiConnectorAuth.GET_TOKEN_MODULE_ID)

        auth.set_key_and_certificate(cert.key, cert.certificate)
        token_string = auth.get_token(seed)

        token = Token(token_string)

        uploader = SiiDocumentUploader(token=token.get_token(), application_name='DAIAERP')
        result = uploader.send_document(user_rut=specific_header_parameters['User']['RUT'], company_rut=sender_parameters['RUT'],
                               document_path='temp/DTE_ENV' + str(dte_object.get_document_id()) + '_ru.xml', doc_id=dte_object.get_document_id())
    logger.debug(f"RESULT {result}")
    return result


RES_DATE = '2022-01-17'
RES_NUMBER = '0'
def generate_xml(folder,pfx_file_path, pfx_password, type=52):
    import ssl
    logger.info(ssl.OPENSSL_VERSION)
    pdf = PDFGenerator()
    envelope = {}
    """ Dump test XML """

    document_count = len(sys.argv) == 6 and int(sys.argv[5])

    if not document_count:
        document_count = 1

    for i in range(1, document_count + 1):
        sender_parameters = {}
        receiver_parameters = {}
        specific_header_parameters = {}
        item_list = {}
        path = 'test/data_' + str(i)
        path = folder

        """ Read test files """
        with open(path + '/user.json', encoding='ISO-8859-1') as json_file:
            user_parameters = json.load(json_file)
        with open(path + '/sender.json', encoding='ISO-8859-1') as json_file:
            sender_parameters = json.load(json_file)
        with open(path + '/receiver.json', encoding='ISO-8859-1') as json_file:
            receiver_parameters = json.load(json_file)
        with open(path + '/items.json', encoding='ISO-8859-1') as json_file:
            item_list = json.load(json_file)
        with open(path + '/references.json', encoding='ISO-8859-1') as json_file:
            reference_list = json.load(json_file)
        with open(path + '/specifics.json', encoding='ISO-8859-1') as json_file:
            specific_header_parameters = json.load(json_file)
        try:
            with open(path + '/discounts.json', encoding='ISO-8859-1') as json_file:
                discounts_parameters = json.load(json_file)
        except:
            discounts_parameters = []
            pass

        caf = DTECAF(parameters={}, signature='', private_key='')
        caf.load_from_XML(path + '/caf_test.xml')

        builder = DTEBuidler()

        """ Bind user information, mocked for this process """
        specific_header_parameters['User'] = {}
        specific_header_parameters['User']['Resolution'] = RES_NUMBER
        specific_header_parameters['User']['ResolutionDate'] = RES_DATE
        specific_header_parameters['User']['RUT'] = user_parameters['RUT']

        documents = builder.build(type, sender_parameters, receiver_parameters, specific_header_parameters,
                                  item_list, reference_list, discounts_parameters, caf)
        """ Primer documento generado """
        _, pretty_dte, dte_object = documents
        logger.info(f"DTE_OBJECT {str(dte_object.dump())}")
        ###@@@pdf = PDFGenerator()
        ###@@@pdf.generate(dte_object)
        """ Add to envelope to be send """
        envelope[i] = dte_object
        if i < document_count:
            print("Cargar documento siguiente ?")
            resp = input()
    # raise ValueError("STOP")
    """ Generate cover (Caratula) """
    cover = DTECover(dtes=envelope, resolution={'Date': RES_DATE, 'Number': RES_NUMBER}, user=user_parameters)

    """ Generate payload to be uploaded (without signature, only tagged) """
    payload = DTEPayload(dtes=envelope, cover=cover, user={}, set_id="Set" + str(type) + "-" + str(document_count))
    siiSignature = SiiPlugin()

    """ Load key """
    cert = CertificateService(pfx_file_path=pfx_file_path, pfx_password=pfx_password)
    cert.generate_certificate_and_key()
    siiSignature.key = cert.key
    siiSignature.cert = cert.certificate

    """ Remove declaration """
    declare = '<?xml version="1.0" encoding="ISO-8859-1"?>'
    payload = payload.dump_without_xml_declaration()

    """ Sign """
    ready_to_upload = siiSignature.sign_tagged_message(payload)

    """ Add declaration back """
    ready_to_upload = declare + '\n' + ready_to_upload

    """ Write ready-to-upload XML  (without signature) """
    doc_path = 'temp/DTE_ENV' + str(dte_object.get_document_id()) + '_ru.xml'
    myXML = open(doc_path, "w", encoding="ISO-8859-1")
    myXML.write(ready_to_upload)
    logger.info(f"PAYLOAD	 {str(ready_to_upload)}")
    """ Get token """
    auth = SiiConnectorAuth(module=SiiConnectorAuth.GET_SEED_MODULE_ID)
    seed = auth.get_seed()
    auth = SiiConnectorAuth(module=SiiConnectorAuth.GET_TOKEN_MODULE_ID)

    auth.set_key_and_certificate(cert.key, cert.certificate)
    token_string = auth.get_token(seed)

    token = Token(token_string)

    uploader = SiiDocumentUploader(token=token.get_token(), application_name='DAIAERP')
    result = uploader.send_document(user_rut=specific_header_parameters['User']['RUT'], company_rut=sender_parameters['RUT'],
                           document_path='temp/DTE_ENV' + str(dte_object.get_document_id()) + '_ru.xml', doc_id=dte_object.get_document_id())
    logger.info(f"RESULT {result}")



if __name__ == "__main__":
    #
    key = """
-----BEGIN RSA PRIVATE KEY-----
MIIBOQIBAAJBAL3Md/Di8q9BoKbmZ0hr7uxff9gAQq3kx5NQ7ZpA5soQOBUa8+9f
1tpQVKkGKujB7w1/LbtgVOVgOgblYQ7EvO8CAQMCQH6IT/XsocorwG9ERNryn0g/
qpAALHPt2mI187wrRIa0VLpbhS/eYrjIMQuahA5MwJ5PhM5PGc4ceJx3n1vb2wsC
IQDh8aKyoQLZ3b6Rppx516X0VOEbbT1ztEA1hUaLMgk3GQIhANcL7vmGj2jnZXlx
Aer7qNnLJssYrDp79U+W62bS8b1HAiEAlqEXIcCskT5/C8RoUTpuouNAvPN+TSLV
eQOEXMwGJLsCIQCPXUn7rwpF75j7oKvx/Rs73MSHZcgm/U41D0eZ4fZ+LwIge9sm
asGh03WlyLC7U7V2ItLKF0HfWXE6M2+ZEmLE5Tc=
-----END RSA PRIVATE KEY-----"""
    import xmlsec

    # key = xmlsec.Key.from_file("../../client_ssl.pem", xmlsec.constants.KeyDataFormatPem, "2022")
    key = xmlsec.Key.from_memory(data=key, format=xmlsec.KeyFormat.PEM, password=None)
    manager = xmlsec.KeysManager()
    manager.add_key(key)
    import base64
    with open("sample_data.json", "r") as fd:
        data = json.load(fd)
    data["caf"] = base64.b64decode(data["caf"]).decode("utf-8")
    data["config"]["pem"] = base64.b64decode(data["config"]["pem"]).decode("utf-8")
    upload_xml(data)
    #generate_xml(folder="XMLs/1", pfx_file_path="../../mi_certificado_firma.cl.pfx", pfx_password="2022")