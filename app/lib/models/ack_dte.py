import os
import datetime
from typing import List, Dict
from lib.models.dte_base import DTEBase
from lib.models.dte import DTECAF, DTEBuidler, DTECover, DTEPayload, DTE, DTEPerson
from ..zeep.sii_plugin import SiiPlugin
from lxml import etree

URI_TAG = '{{URI}}'
DTE_SII_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
#DTE_SII_DATE_FORMAT = '%Y-%m-%d'
DTE_SII_DATE_FORMAT_SHORT = '%Y-%m-%d'

""" Future : Database """
FILE_DIR = os.path.dirname(os.path.realpath(__file__))


def build_signature(document_id):
    sii = SiiPlugin()
    template_signature = sii.read_file().decode('iso-8859-1')
    template_signature = template_signature.replace(URI_TAG, document_id)
    return template_signature

ACK_HEADER = '<RespuestaDTE xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte RespuestaEnvioDTE_v10.xsd" version="1.0">'
class DTEAck(DTEBase):
   __responses = {        
            1:"",
            2:""
        }
   __receiver = None

   def __init__(self, receiver:DTEPerson):
       self.__receiver = receiver

   def dump(self, content:str):
       document_id = "ACK1"
       return ACK_HEADER + \
           "<Resultado ID=\"" + document_id + "\">" + \
           content + \
           "</Resultado>" + \
           build_signature(document_id) + \
           "</RespuestaDTE>"

   def generate_response_for_XML(self, xml_received_path:str, response_id:int):
        builder = DTEBuidler()
        filename = os.path.basename(xml_received_path)
        payload, documents = builder.from_file(xml_received_path)
        """ Recuparemos solamente los DTE """
        documents = [c for a,b,c in documents]
        
        return self.generate_response_for_document(payload, documents, response_id, filename)

   def generate_response_for_document(self, payload:Dict, documents:List[DTE], response_id:int, filename):
       response = ""
       document_received = documents[0]
       document_parameters = document_received.to_template_parameters()

       caratula = "<Caratula version='1.0'>" + \
            "<RutResponde>" + self.__receiver.get_attr("RUT") + "</RutResponde>" + \
            "<RutRecibe>" + document_received.get_document_sender() + "</RutRecibe>" + \
            "<IdRespuesta>" + str(response_id) + "</IdRespuesta>" + \
            "<NroDetalles>" + "1" + "</NroDetalles>" + \
            "<TmstFirmaResp>" + str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT)) + "</TmstFirmaResp>" + \
        "</Caratula>"

       rcp_dte = ""
       res_dte = ""
       for document_received in documents:
           document_parameters = document_received.to_template_parameters()

           validation_state = "0"
           if self.__receiver.get_attr("RUT") != document_parameters['Receiver']['RUT']:
               """ RUT recibidor no corresponde """
               validation_state = "3"

           res_dte = res_dte + "<ResultadoDTE>" + \
               "<TipoDTE>" + str(document_received.get_document_type()) + "</TipoDTE>" + \
               "<Folio>" + str(document_parameters['DocumentNumber']) + "</Folio>" + \
               "<FchEmis>" + document_parameters['Header']['IssuedDate'] + "</FchEmis>" + \
               "<RUTEmisor>" +  document_parameters['Sender']['RUT'] + "</RUTEmisor>" + \
               "<RUTRecep>" +  document_parameters['Receiver']['RUT'] + "</RUTRecep>" + \
               "<MntTotal>" +  str(document_received.get_total_amount()) + "</MntTotal>" + \
               "<CodEnvio>" +  "3074439" + "</CodEnvio>"

           if validation_state != "0":
               res_dte = res_dte + "<EstadoDTE>" +  "2" + "</EstadoDTE>"
               res_dte = res_dte + "<EstadoDTEGlosa>" +  "0" + "</EstadoDTEGlosa>"
               res_dte = res_dte + "<CodRchDsc>" + "-1" + "</CodRchDsc>"
           else:
                res_dte = res_dte + "<EstadoDTE>" +  "0" + "</EstadoDTE>"
                res_dte = res_dte + "<EstadoDTEGlosa>" +  "0" + "</EstadoDTEGlosa>"
                              
           res_dte = res_dte + "</ResultadoDTE>"

           rcp_dte = rcp_dte +  "<RecepcionDTE>" + \
                "<TipoDTE>" + str(document_received.get_document_type()) + "</TipoDTE>" + \
                "<Folio>" + str(document_parameters['DocumentNumber']) + "</Folio>" + \
                "<FchEmis>" + document_parameters['Header']['IssuedDate'] + "</FchEmis>" + \
                "<RUTEmisor>" +  document_parameters['Sender']['RUT'] + "</RUTEmisor>" + \
                "<RUTRecep>" +  document_parameters['Receiver']['RUT'] + "</RUTRecep>" + \
                "<MntTotal>" +  str(document_received.get_total_amount()) + "</MntTotal>" + \
                "<EstadoRecepDTE>" +  validation_state + "</EstadoRecepDTE>" + \
                "<RecepDTEGlosa>" + "" + "</RecepDTEGlosa>" + \
                "</RecepcionDTE>"

           
       content = rcp_dte
       envio = "<RecepcionEnvio>" + \
           "<NmbEnvio>" + filename + "</NmbEnvio>" + \
           "<FchRecep>" + str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT)) + "</FchRecep>" + \
           "<CodEnvio>" + str(response_id) + "</CodEnvio>" + \
           "<EnvioDTEID>" + "SetDoc" + "</EnvioDTEID>" + \
           "<Digest>" + document_received._sii_signature['DigestValue'] + "</Digest>" + \
           "<RutEmisor>" +  document_parameters['Sender']['RUT'] + "</RutEmisor>" + \
           "<RutReceptor>" +  self.__receiver.get_attr("RUT") + "</RutReceptor>" + \
           "<EstadoRecepEnv>" + "0" + "</EstadoRecepEnv>" + \
           "<RecepEnvGlosa>" + "" + "</RecepEnvGlosa>" + \
           "<NroDTE>" + str(len(documents)) + "</NroDTE>" + \
           content + \
           "</RecepcionEnvio>"

       #response = caratula + envio
       response = caratula + res_dte

       return response


COM_ACK_HEADER = '<EnvioRecibos xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte RespuestaEnvioDTE_v10.xsd" version="1.0">'
class DTEComAck(DTEBase):
    __receiver = None

    def __init__(self, receiver:DTEPerson):
        self.__receiver = receiver

    def dump(self, content:str):
        document_id = "SR1"
        return COM_ACK_HEADER + \
            "<SetRecibos ID='" + document_id + "'>" + \
            content + \
            "</SetRecibos>" + \
            build_signature(document_id) + \
            "</EnvioRecibos>"

    def generate_response_for_XML(self, xml_received_path:str, response_id:int):
        builder = DTEBuidler()
        filename = os.path.basename(xml_received_path)
        payload, documents = builder.from_file(xml_received_path)
        """ Recuparemos solamente los DTE """
        documents = [c for a,b,c in documents]
        
        return self.generate_response_for_document(payload, documents, response_id, filename)

    def generate_response_for_document(self, payload:Dict, documents:List[DTE], response_id:int, filename):
        response = ""
        document_received = documents[0]
        document_parameters = document_received.to_template_parameters()
        print(payload['TmstFirmaEnv'])

        caratula = "<Caratula version='1.0'>" + \
            "<RutResponde>" + self.__receiver.get_attr("RUT") + "</RutResponde>" + \
            "<RutRecibe>" + document_received.get_document_sender() + "</RutRecibe>" + \
            "<TmstFirmaEnv>" + payload['TmstFirmaEnv'] + "</TmstFirmaEnv>" + \
        "</Caratula>"

        content = ""
        k = 1
        for document_received in documents:
            recibo_id = "R" + str(k)
            res_recibo = "<Recibo version='1.0'>" + \
               "<DocumentoRecibo ID=\"" + recibo_id + "\">" + \
                   "<TipoDoc>" + str(document_received.get_document_type()) + "</TipoDoc>" + \
                   "<Folio>" + str(document_parameters['DocumentNumber']) + "</Folio>" + \
                   "<FchEmis>" + document_parameters['Header']['IssuedDate'] + "</FchEmis>" + \
                   "<RUTEmisor>" +  document_parameters['Sender']['RUT'] + "</RUTEmisor>" + \
                   "<RUTRecep>" +  document_parameters['Receiver']['RUT'] + "</RUTRecep>" + \
                   "<MntTotal>" +  str(document_received.get_total_amount()) + "</MntTotal>" + \
                   "<Recinto>" +  "Casa matriz" + "</Recinto>" + \
                   "<RutFirma>" +  document_parameters['Header']['Specifics']['User']['RUT'] + "</RutFirma>" + \
                   "<Declaracion>" +  "El acuse de recibo que se declara en este acto, de acuerdo a lo dispuesto en la letra b) del Art. 4, y la letra c) del Art. 5 de la Ley 19.983, acredita que la entrega de mercaderias o servicio(s) prestado(s) ha(n) sido recibido(s)." + "</Declaracion>" + \
                   "<TmstFirmaRecibo>" + str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT)) + "</TmstFirmaRecibo>" + \
               "</DocumentoRecibo>" + \
                build_signature(recibo_id) + \
               "</Recibo>"

            content = content + res_recibo
            k = k + 1

        response = caratula + content

        return response