from typing import Dict, List
from lib.models.dte_base import DTEBase
from lib.models.dte import DTEPerson, DTE

URI_TAG = '{{URI}}'
DTE_SII_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
#DTE_SII_DATE_FORMAT = '%Y-%m-%d'
DTE_SII_DATE_FORMAT_SHORT = '%Y-%m-%d'

VENTA_HEADER = '<LibroCompraVenta xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte LibroCV_v10.xsd" version="1.0">'


def build_signature(document_id):
	sii = SiiPlugin()
	template_signature = sii.read_file().decode('iso-8859-1')
	template_signature = template_signature.replace(URI_TAG, document_id)
	return template_signature

def sanitize_string(string):
	string = string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
	return string

class LibVenta(DTEBase):
	def dump(self) -> str:
		return VENTA_HEADER + "" + "</LibroCompraVenta>"

class LibCaratula(DTEBase):
	"""	<Caratula>
			<RutEmisorLibro>77368325-5</RutEmisorLibro>
			<RutEnvia>25656563-3</RutEnvia>
			<PeriodoTributario>2022-002</PeriodoTributario>
			<FchResol>2014-08-22</FchResol>
			<NroResol>80</NroResol>
			<TipoOperacion>VENTA</TipoOperacion>
			<TipoLibro>MENSUAL</TipoLibro>
			<TipoEnvio>TOTAL</TipoEnvio>
		</Caratula>
	"""
	HEADER_CARATULA = "Caratula"
	_sender = None
	_resol_params = {}
	_operation_type = ""
	_book_type = ""
	_payload_type = ""
	_periodo = ""

	def __init__(self, sender:Dict, resol_params:Dict, operation_type:str='VENTA', book_type:str='MENSUAL', payload_type:str='TOTAL', periodo:str=""):
		self._sender = sender
		self._resol_params = resol_params
		self._operation_type = operation_type
		self._book_type = book_type
		self._periodo = periodo

		print("")

	def dump(self):
		return 	"<" + HEADER_CARATULA + ">" + \
			"<RutEmisorLibro>"+ sender['RutCompany'] +"</RutEmisorLibro>" + \
			"<RutEnvia>"+ sender['RutUser'] +"</RutEnvia>" + \
			"<PeriodoTributario>" + periodo + "</PeriodoTributario>" + \
			"<FchResol>"+ self._resol_params['fecha'] +"</FchResol>" + \
			"<NroResol>"+ self._resol_params['numero'] +"</NroResol>" + \
			"<TipoOperacion>"+ self._operation_type + "</TipoOperacion>" + \
			"<TipoLibro>"+ self._book_type +"</TipoLibro>" + \
			"<TipoEnvio>" + self._payload_type +"</TipoEnvio>" + \
			"</" +  HEADER_CARATULA + ">"

class LibResumen(DTEBase):
	"""
	<ResumenPeriodo>
		<TotalesPeriodo>
			<TpoDoc>110</TpoDoc>
			<TotDoc>52</TotDoc>
			<TotMntExe>0</TotMntExe>
			<TotMntNeto>693373225</TotMntNeto>
			<TotMntIVA>0</TotMntIVA>
			<TotMntTotal>693373225</TotMntTotal>
		</TotalesPeriodo>
		<TotalesPeriodo>
			<TpoDoc>111</TpoDoc>
			<TotDoc>1</TotDoc>
			<TotMntExe>0</TotMntExe>
			<TotMntNeto>698178</TotMntNeto>
			<TotMntIVA>0</TotMntIVA>
			<TotMntTotal>698178</TotMntTotal>
		</TotalesPeriodo>
	</ResumenPeriodo>
	"""
	def __init__(self, dtes:List[DTE]):
		print("")

	def dump_item(self, dte:DTE):
		""" Dump del Detalle """
		dte_params = dte.to_template_parameters()
		details = dte.get_total_amount()

		return "<TpoDoc>" + dte_params['DocumentNumber'] + "</TpoDoc>" + \
			"<NroDoc>" + dte_params['DocumentNumber']  + "</NroDoc>" + \
			"<TasaImp>" + "19" + "</TasaImp>" + \
			"<FchDoc>" + dte_params['Header']['IssuedDate']  + "</FchDoc>" + \
			"<RUTDoc>" + dte_params['Sender']['RUT'] + "</RUTDoc>" + \
			"<RznSoc>" + dte_params['Sender']['Name'] + "</RznSoc>" + \
			"<MntExe>" + details['TotalExento'] + "</MntExe>" + \
			"<MntNeto>" + details['Net'] + "</MntNeto>" + \
			"<MntIVA>" + details['IVA'] + "</MntIVA>" + \
			"<MntTotal>" + details['Total'] + "</MntTotal>"

	def dump(self):
		""" Dump del Detalle """
		dump = ""

		for dte in _dtes:
			dump = dump + "<TotalesPeriodo>" + \
				self.dump_item(dte) + \
				"</TotalesPeriodo>"

		return dump

class LibDetalle(DTEBase):
	"""
		<Detalle>
			<TpoDoc>110</TpoDoc>
			<NroDoc>1829</NroDoc>
			<TasaImp>19</TasaImp>
			<FchDoc>2017-07-02</FchDoc>
			<RUTDoc>76087419-1</RUTDoc>
			<RznSoc>EXPORTADORA ANDINEXIA S.A.</RznSoc>
			<MntExe>0</MntExe>
			<MntNeto>13717106</MntNeto>
			<MntIVA>0</MntIVA>
			<MntTotal>13717106</MntTotal>
		</Detalle>
	"""
	_dtes:List[DTE] = None

	def __init__(self, dtes:List[DTE]):
		print("")

	def dump_item(self, dte:DTE):
		""" Dump del Detalle """
		dte_params = dte.to_template_parameters()
		details = dte.get_total_amount()

		return "<TpoDoc>" + dte_params['DocumentNumber'] + "</TpoDoc>" + \
			"<NroDoc>" + dte_params['DocumentNumber']  + "</NroDoc>" + \
			"<TasaImp>" + "19" + "</TasaImp>" + \
			"<FchDoc>" + dte_params['Header']['IssuedDate']  + "</FchDoc>" + \
			"<RUTDoc>" + dte_params['Sender']['RUT'] + "</RUTDoc>" + \
			"<RznSoc>" + dte_params['Sender']['Name'] + "</RznSoc>" + \
			"<MntExe>" + details['TotalExento'] + "</MntExe>" + \
			"<MntNeto>" + details['Net'] + "</MntNeto>" + \
			"<MntIVA>" + details['IVA'] + "</MntIVA>" + \
			"<MntTotal>" + details['Total'] + "</MntTotal>"

	def dump(self):
		""" Dump del Detalle """
		dump = ""

		for dte in _dtes:
			dump = dump + "<Detalle>" + \
				self.dump_item(dte) + \
				"</Detalle>"

		return dump

class LibPayload(DTEBase):
	_doc_id = 'SetDoc'
	_caratula = '<Caratula></Caratula>'
	_resumen = '<ResumenPeriodo></ResumenPeriodo>'
	_detalle = '<Detalle></Detalle>'

	def __init__(self, doc_id, caratula:LibCaratula, resumen:LibResumen, detalle:LibDetalle):
		self._doc_id = doc_id
		self._caratula = caratula
		self._resumen = resumen
		self._detalle = detalle

	def dump(self):
		return '<EnvioLibro ID="' + self._doc_id + '">' + \
			self._caratula.dump() + \
			self._resumen.dump() + \
			self._detalle.dump() + \
			"</EnvioLibro>"

