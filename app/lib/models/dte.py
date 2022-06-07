#!/usr/bin/env python
from typing import Dict, List
import datetime
import json
import os
from lxml import etree
from ..zeep.sii_plugin import SiiPlugin

"""
General format :

<DTE version=1.0”>
 <Documento ID=””>
	 <Encabezado>... </Encabezado>
	 <DetalleFactura>... </DetalleFactura>
	 <DescuentoRecargoGlobal>... </DescuentoRecargoGlobal>
	 <Referencia>... </Referencia>
	 <TED>... </TED> /* Timbre Electrónico DTE
	 <TmstFirma> ... </TmstFirma> /* TimeStamp firma del DTE
 </Documento>
<Signature>  	Firma digital sobre
  <Documento>... </Documento>
  </Signature>
</DTE>

"""
""" AAAA-MM-DDTHH24:MI:SS """
URI_TAG = '{{URI}}'
DTE_SII_DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
#DTE_SII_DATE_FORMAT = '%Y-%m-%d'
DTE_SII_DATE_FORMAT_SHORT = '%Y-%m-%d'

""" Future : Database """
FILE_DIR = os.path.dirname(os.path.realpath(__file__))
with open(FILE_DIR + '/database/codes.json', encoding="utf-8") as json_file:
	db_codes = json.load(json_file)

def build_skippable_properties(header) -> List:
	specifics = header._specifics
	document_type = header.dte_document_type
	skip_props = []

	if int(document_type) == 52:
		""" Guia de despacho """
		""" Buscamos el tipo de traslado """
		""" MovementType
			<option value="1">Operación constituye venta</option>
			<option value="2">Ventas por efectuar</option>
			<option value="3">Consignaciones</option>
			<option value="4">Entrega gratuita</option>
			<option value="5">Traslados internos</option>
			<option value="6">Otros traslados no venta</option>
			<option value="7">Guía de devolución</option>
			<option value="8">Traslado para exportación. (no venta)</option>
			<option value="9">Venta para exportación</option>
		"""
		""" ExpeditionType
			<option value="1">Despacho por cuenta del receptor del documento</option>
			<option value="2">Despacho por cuenta del emisor a instalaciones del cliente</option>
			<option value="3">Despacho por cuenta del emisor a otras instalaciones</option>
		"""
		movement_type = int(specifics['MovementType'])
		if movement_type in [5, 6, 7, 8]:
			""" No mostrar precio unitario """
			skip_props.append("UnitPrice")
			skip_props.append("ExpeditionType")
		else:
			expedition_type = int(specifics['ExpeditionType'])

	return skip_props

def build_signature(document_id):
	sii = SiiPlugin()
	template_signature = sii.read_file().decode('iso-8859-1')
	template_signature = template_signature.replace(URI_TAG, document_id)
	return template_signature

def sanitize_string(string, size=80):
	""" Remplazamos los caracteres especiales y truncamos las cadenas largas """
	string = string.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")[:size]
	string = string.strip()
	return string

class DTEPerson:
	_type = 0
	__types = ['Receiver', 'Sender']
	_parameters = [];

	__markup = {'Receiver': {
								'Type':'Receptor',
								'RUT':'RUTRecep',
								'Name':'RznSocRecep',
								'Activity':'GiroRecep',
								'Address':'DirRecep',
								'City':'CmnaRecep',
								'State':'CiudadRecep',
								'Contact': 'Contacto',
								'Email': 'CorreoRecep'
							},
				'Sender': {
								'Type':'Emisor',
					 			'RUT':'RUTEmisor',
								'Name':'RznSoc',
								'Activity':'GiroEmis',
								'Acteco':'Acteco',
								'SPE_Export': '$GuiaExport',
								'Address':'DirOrigen',
								'City':'CmnaOrigen',
								'State':'CiudadOrigen',
								'Phone': '$Telefono',
								'Contact': '$Contacto'
							}
				}

	"""
	Acteco
	Se acepta un máximo de 4 Códigos de actividad económica del emisor del DTE.
	Se puede incluir sólo el código que corresponde a la transacción
	"""

	def __init__(self, type, parameters):
		self._type = type
		self._parameters = parameters

	def get_attr(self, attr):
		try:
			return self._parameters[attr]
		except:
			return '';

	def dump(self):
		outside_markup = self.__markup[self.__types[self._type]]['Type']
		dumped = '<' + outside_markup + '>'
		item_props = {}
		for param in self._parameters:
			try:
				prop_order = -1
				markup = str(self.__markup[self.__types[self._type]][param])
				value = str(self._parameters[param])
				prop_order = list(self.__markup[self.__types[self._type]].values()).index(markup)
				""" Condición especial """
				if markup.startswith("$"):
					markup = markup.replace("$", "")
					value = self.get_special_property(value, markup)
				else:
					value = sanitize_string(value)

				if len(value) > 0:
					item_props[prop_order] = {'markup': markup, 'value': value}
			except KeyError:
				""" Should not be output"""
				pass

		""" Ordenamos """
		item_props = dict(sorted(item_props.items()))
		for k in item_props:
			prop = item_props[k]
			dumped = dumped + "<" + prop['markup'] + ">" + prop['value'] + "</" + prop['markup'] + ">"

		dumped = dumped + '</' + outside_markup + '>'
		return dumped

	def get_special_property(self, value, markup):
		if markup == 'GuiaExport':
			""" Fijo para traslado de exportación """
			return "<CdgTraslado>1</CdgTraslado>"
		else:
			return ''

	def get_property_by_markup(self, type, search_markup):
		for property, markup in self.__markup[self.__types[type]].items():
			if markup == search_markup:
				return property

	def from_xml_parameters(self, type, xml_parameters):
		parameters = {}

		for markup in xml_parameters:
			prop = self.get_property_by_markup(type, markup)
			if prop is not None:
				parameters[prop] = xml_parameters[markup]

		self._parameters = parameters
		return parameters

class DTEHeader:
	""" Document identity, composed of sender, reciber information, document type, and total amount """
	sender = DTEPerson(1, None)
	receiver = DTEPerson(0, None)
	dte_document_type = 0
	dte_document_number = 0
	_dte_export_type = 0
	_dte_export_indicator = 0
	_dte_payment_method = 0
	_dte_expiry_date = 0
	_net_amount = 0
	_tax_rate = 0
	_taxes = 0
	total_amount = 0

	_specifics = None
	totales = {}

	__valid_document_types = {
	33: 'Factura Electrónica',
	34: 'Factura No Afecta o Exenta Electrónica',
	43: 'Liquidación-Factura Electrónica',
	46: 'Factura de Compra Electrónica',
	52: 'Guía de Despacho Electrónica',
	56: 'Nota de Débito Electrónica',
	61: 'Nota de Crédito Electrónica',
	110: 'Factura de Exportación',
	111: 'Nota de Débito de Exportación',
	112: 'Nota de Crédito de Exportación'
	}


	"""
	MovementType <IndTraslado>
	1:  Operación constituye
	2:  Ventas por efectuar
	3:  Consignaciones
	4:  Entrega gratuita
	5: Traslados internos
	6: Otros traslados no venta
	7: Guía de devolución
	8: Traslado para exportación. (no venta)
	9: Venta para exportación
	"""
	"""
	ExpeditionType <TipoDespacho>
	1: Despacho por cuenta del receptor del documento (cliente o vendedor  en caso de Facturas de compra.)
	2: Despacho por cuenta del  emisor a instalaciones del  cliente
	3: Despacho por cuenta del emisor a otras instalaciones (Ejemplo: entrega en Obra)
	"""
	"""
	PrintedFormat <TpoImpresion>
	T: Ticket
	N: Normal
	"""

	__specifics_by_document_type = {
									30: {},
									32: {},
									33: {},
									34: {},
									35: {},
									38: {},
									39: {},
									40: {},
									41: {},
									45: {},
									46: {},
									48: {},
									50: {},
									52: {},
									55: {},
									56: {},
									60: {},
									61: {},
									103: {},
									110: {},
									111: {},
									112: {},
									801: {},
									802: {},
									803: {},
									804: {},
									805: {},
									806: {},
									807: {},
									808: {},
									809: {},
									810: {},
									811: {},
									812: {},
									813: {},
									814: {},
									815: {},
									914: {},
									52: {
										'ExpeditionType':'TipoDespacho',
										'MovementType':'IndTraslado',
										'PrintedFormat': 'TpoImpresion'
										},
									0: {
										'User-RUT': 'RutEnvia',
										'User-Resolution': 'NroResol',
										'User-ResolutionDate' : 'FchResol',
										'IssueDate' : 'FchEmis',
										'LimitDate': 'FchVenc',
										'TimeStampUpload': 'TmstFirmaEnv'
										}
								}
	__property_type_by_specific = {
								'ShippingPort':'Port',
								'LandingPort':'Port',
								'ExpeditionType': 'Description',
								'MovementType': 'Description'
								}
	comment = ''

	def __init__(self, sender, receiver, document_type, document_number, payment_method, expiry_date, specific_parameters, totales):
		""" specific_parameters parameter should contains document type based parameters """
		assert(document_type in self.__valid_document_types)
		self.sender = sender
		self.receiver = receiver

		if 'DocumentType' in specific_parameters:
			self.dte_document_type = int(specific_parameters['DocumentType'])
		else:
			self.dte_document_type = document_type

		self.dte_document_number = document_number
		self._dte_payment_method = payment_method
		self._dte_expiry_date = expiry_date
		self._specifics = specific_parameters
		self.totales = totales

		try:
			self.comment = specific_parameters['Comment']
		except:
			pass

	def get_specifics_for_display(self):
		human_readable_specifics = {}
		for key in self._specifics:
			human_readable_specifics[key] = self.translate_specific_to_human_readable(key, self._specifics[key])
			human_readable_specifics[key+"_ID"] = self._specifics[key]
		return human_readable_specifics

	def translate_specific_to_human_readable(self, key, value):
		try:
			""" Get property type """
			property_type = self.__property_type_by_specific[key]
			if property_type == 'Description':
				""" In that case we need to get description according to searched property """
				properties = db_codes[property_type][key]
			elif property_type == 'TipoDoc':
				properties = db_codes[property_type][key]
			else:
				properties = db_codes[property_type]
			""" Value should be the code """
			return properties[value]
		except:
			return value

	def dump_specifics(self):
		dumped = ''
		item_props = {}
		for param in self._specifics:
			try:
				markup = ''
				value = ''
				prop_order = -1

				if param in self.__specifics_by_document_type[self.dte_document_type]:
					""" Specific """
					markup = str(self.__specifics_by_document_type[self.dte_document_type][param])
					""" El indice de la propriedad, para ordenar """
					prop_order = list(self.__specifics_by_document_type[self.dte_document_type].values()).index(markup)

					value =  self._specifics[param]

				if len(markup) > 0 and len(str(value)) > 0:
					""" Dump with corresponding markup """
					sanitized_value = sanitize_string(str(value))
					""" Asignamos a la lista de propriedades """
					item_props[prop_order] = {'markup': markup, 'value': sanitized_value}
			except Exception as e:
				print(e)
				pass
		""" Ordenamos """
		item_props = dict(sorted(item_props.items()))
		for k in item_props:
			prop = item_props[k]
			dumped = dumped + "<" + prop['markup'] + ">" + prop['value'] + "</" + prop['markup'] + ">"
		return dumped

	def dump(self):
		return '<Encabezado>' + self.dump_document_identification() + \
		self.sender.dump()  + \
		self.receiver.dump() + \
		self.dump_totales() + \
		 '</Encabezado>'

	def dump_totales(self):
		if int(self.dte_document_type) == 52:
			return '<Totales>' + \
				'<IVA>0</IVA>' + \
				'<MntTotal>0</MntTotal>' + \
			'</Totales>'
		else:
			return '<Totales><MntNeto>' + str(self.totales['Net']) + '</MntNeto>' + \
							'<MntExe>' + str(round(self.totales['TotalExento'])) + '</MntExe>' + \
							'<TasaIVA>' + str(self.totales['Rate']) + '</TasaIVA>' + \
							'<IVA>' + str(round(self.totales['IVA'])) + '</IVA>' + \
							'<MntTotal>' + str(round(self.totales['Total'])) + '</MntTotal>' + \
		 				'</Totales>'

	def dump_document_identification(self, skip_props=[]):
		return '<IdDoc>' + self.dump_document_type() + \
						self.dump_document_number() + \
						self.dump_issue_date() + \
						self.dump_specifics() + \
						self.dump_payment_method() + \
						self.dump_expiry_date() + \
						'</IdDoc>'

	def dump_document_number(self):
		return '<Folio>'+ str(self.dte_document_number) +'</Folio>'

	def dump_document_type(self):
		return '<TipoDTE>' + str(self.dte_document_type) + '</TipoDTE>'

	def dump_issue_date(self):
		return '<FchEmis>' + self.get_issue_date() + '</FchEmis>'

	def get_issue_date(self):
		date = ''
		if 'IssueDate' in self._specifics:
			date = self._specifics['IssueDate']
		else:
			""" Now """
			date = str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT_SHORT))
		return date

	def get_expiry_date(self):
		date = ''
		if 'LimitDate' in self._specifics:
			date = self._specifics['LimitDate']
		else:
			""" Now """
			date = str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT_SHORT))
		return date

	def dump_payment_method(self):
		return '<FmaPago>' + str(self._dte_payment_method) + '</FmaPago>'

	def dump_expiry_date(self):
		return '<FchVenc>' + str(self._dte_expiry_date) + '</FchVenc>'

	def get_property_by_markup(self, document_type, search_markup):
		for property, markup in self.__specifics_by_document_type[document_type].items():
			if markup == search_markup:
				return property
		for property, markup in self.__specifics_by_document_type[0].items():
			if markup == search_markup:
				return property

	def load_specifics_from_xml_parameters(self, document_type, parameters):
		for i in parameters:
			property = self.get_property_by_markup(document_type, i)
			if property is not None:
				""" Sub array """
				if '-' in property:
					sub = property.split('-')[0]
					prop = property.split('-')[1]
					""" Create sub array """
					if sub not in self._specifics:
						self._specifics[sub] = {}
					self._specifics[sub][prop] = parameters[i]
				else:
					self._specifics[property] = parameters[i]

class DTEDiscount:
	__markup = {
		'Index': 'NroLinDR',
		'DiscountType' : 'TpoMov',
		'Case' : 'GlosaDR',
		'DiscountValueType': 'TpoValor',
		'DiscountValue': 'ValorDR',
		'ForExento': 'IndExeDR'
	}

	_parameters = {}

	def __init__(self, parameters):
		self._parameters = parameters

	def dump_parameters(self):
		result = ''
		for p in self._parameters:
			try:
				markup = self.__markup[p]
			except:
				markup = p
				pass

			tag_value = self._parameters[p] or ""

			result = result + "<" + markup + ">" + tag_value + "</" + markup + ">"

		return result

	def from_xml_tags(self, xml_tags:Dict):
		self._parameters = {}
		for k in xml_tags:
			for p in self.__markup:
				tag = self.__markup[p] 
				if tag == k:
					self._parameters[p] = xml_tags[k]
		return self._parameters

	def get_discount_value(self):
		discount_type = self._parameters['DiscountValueType']
		discount_value = int(self._parameters['DiscountValue'])
		for_exent = 0

		if 'ForExento' in self._parameters:
			for_exent = self._parameters['ForExento']

		return discount_type, discount_value, for_exent

	def dump(self):
		return '<DscRcgGlobal>' + self.dump_parameters() + '</DscRcgGlobal>'

class DTEReference:
	__markup = {
		'Index': 'NroLinRef',
		'DocumentType' : 'TpoDocRef',
		'Folio' : 'FolioRef',
		'Date': 'FchRef',
		'ReferenceCode': 'CodRef',
		'Case' : 'RazonRef'
	}
	_parameters = {}

	def __init__(self, parameters):
		self._parameters = parameters

	def dump_parameters(self):
		result = ''
		if 'Index' not in self._parameters:
			""" Sin indice de referencia """
			result = "<NroLinRef>1</NroLinRef>"

		for p in self._parameters:
			markup = self.__markup[p]
			result = result + "<" + markup + ">" + self._parameters[p] + "</" + markup + ">"

		return result

	def from_xml_tags(self, xml_tags:Dict):
		self._parameters = {}
		for k in xml_tags:
			for p in self.__markup:
				tag = self.__markup[p] 
				if tag == k:
					self._parameters[p] = xml_tags[k]
		return self._parameters

	def dump(self):
		return '<Referencia>' + self.dump_parameters() + '</Referencia>'

class DTEItems:
	"""
	'CodeType':'TpoCodigo',
		EAN13, PLU, DUN14, INT1, INT2, EAN128, etc.
	"""

	"""
	'Exento':'IndExe'
	1: No afecto o exento de IVA  (10)
	2: Producto o servicio no es facturable
	3: Garantía de depósito por envases (Cervezas, Jugos, Aguas Minerales, Bebidas Analcohólicas u otros autorizados por Resolución especial)
	4: Ítem No Venta. (Para facturas y  guías de despacho (ésta última con Indicador Tipo de Traslado de Bienes igual a 1)  y este ítem no será facturando
	5: Ítem a rebajar. Para guías de despacho NO VENTA que rebajan guía anterior. En el área de  referencias se debe indicar la guía anterior.
	6: Producto o servicio no facturable negativo (excepto en liquidaciones-factura)
	"""

	"""
	'ItemPrice':'MontoItem'
	(Precio Unitario  * Cantidad ) – Monto Descuento + Monto Recargo
	"""

	__properties_by_document_type = {
									52: {},
									30: {},
									32: {},
									33: {},
									34: {},
									35: {},
									38: {},
									39: {},
									40: {},
									41: {},
									43: {'LiqDocType':'TpoDocLiq'},
									45: {},
									46: {},
									48: {},
									50: {},
									52: {'QuantityRef': 'QtyRef'},
									55: {},
									56: {},
									60: {},
									61: {},
									103: {},
									110: {},
									111: {},
									112: {},
									801: {},
									802: {},
									803: {},
									804: {},
									805: {},
									806: {},
									807: {},
									808: {},
									809: {},
									810: {},
									811: {},
									812: {},
									813: {},
									814: {},
									815: {},
									914: {},
									0: { 'Index':'NroLinDet',
										'CodeType':'TpoCodigo',
										'Code':'VlrCodigo',
										'Exento':'IndExe',
										'Name':'NmbItem',
										'Description':'DscItem',
										'Quantity':'QtyItem',
										'Unit':'UnmdItem',
										'UnitPrice':'PrcItem',
										'DiscountValor%':'DescuentoPct',
										'_ValorDiscount': 'DescuentoMonto',
										'_GlobalDiscountValue' : '',
										'_GlobalDiscount%' : '',
										'ItemPrice':'!MontoItem'
										}
								}

	_items = None
	_document_type = 0
	_args = []

	def __init__(self, document_type, items, args=[]):
		self._document_type = document_type
		self._items = items
		self._args = args

		""" Actualizar los descuentos """
		for item_key in self._items:
			item = self._items[item_key]
			self._calculate_discount(item)

	def dump_items(self, skip_props=[]):
		dumped = ''
		index = 0
		index_markup = str(self.__properties_by_document_type[0]['Index'])

		for item_key in self._items:
			""" Get item """
			item = self._items[item_key]
			item_props = {}

			if item is not None:
				dumped = dumped + '<Detalle>'
				index = index + 1
				dumped = dumped + '<' + index_markup + '>' + str(index) + '</' + index_markup + '>'
				""" Build with common properties """
				for prop in item:
					if not prop in skip_props:
						try:
							markup = ''
							value = ''
							prop_order = -1

							if prop in self.__properties_by_document_type[0]:
								""" Common property """
								markup = str(self.__properties_by_document_type[0][prop])
								""" El indice de la propriedad, para ordenar """
								prop_order = list(self.__properties_by_document_type[0].values()).index(markup)
							elif prop in self.__properties_by_document_type[self._document_type]:
								""" Specific """
								markup = str(self.__properties_by_document_type[self._document_type][prop])
								""" El indice de la propriedad, para ordenar """
								prop_order = list(self.__properties_by_document_type[self._document_type].values()).index(markup)

							if '!' in markup:
								value = self.calculated_field(prop, item)
								""" Borramos el marcador de calculo """
								markup = markup.replace('!', '')
							else:
								value = item[prop]

							if len(markup) > 0 and len(str(value)) > 0:
								""" Dump with corresponding markup """
								sanitized_value = sanitize_string(str(value))
								""" Asignamos a la lista de propriedades """
								item_props[prop_order] = {'markup': markup, 'value': sanitized_value}
						except Exception as e:
							print(e)
							pass
			""" Ordenamos """
			item_props = dict(sorted(item_props.items()))
			for k in item_props:
				prop = item_props[k]
				dumped = dumped + "<" + prop['markup'] + ">" + prop['value'] + "</" + prop['markup'] + ">"
			dumped = dumped + "</Detalle>"
		return dumped

	def _item_is_exento(self, item) -> bool:
		return 'Exento' in item and item['Exento'] == '1'

	def _calculate_discount(self, item, add_global_discount=True) -> int:
		""" Calcula y almacena el monto de descuento por item """
		discount = 0
		if 'Quantity' in item and 'UnitPrice' in item:
			total_item = int(item['Quantity']) * int(item['UnitPrice'])
		else:
			total_item = 0

		if 'DiscountValor%' in item:
			discount = item['DiscountValor%'] + '%'
		elif 'DescuentoMonto' in item:
			discount = item['DescuentoMonto']
			discount = int(discount)

		if isinstance(discount, str) and '%' in discount:
			percent_disc = int(discount.replace('%', ''))
			discount = int(round((total_item * percent_disc / 100), 0))

		if '_ValorDiscount' in item:
			item['_ValorDiscount'] = discount

		""" Buscamos descuentos globales """
		discount_global_value = 0

		if 'global_discounts' in self._args and add_global_discount:
			discounts = self._args['global_discounts']
			for d in discounts:
				""" Aplicar descuentos globales """
				discount_type, discount_value, for_exent = d.get_discount_value()
				if for_exent == 0 and self._item_is_exento(item):
					continue
				if discount_type == '%' and for_exent == 0:
					item['_GlobalDiscount%'] = str(discount_value)
					discount_global_value = discount_global_value + int(round(total_item * discount_value / 100,0))
				else:
					discount_global_value = discount_global_value + int(discount_value)
			if discount_global_value > 0:
				item['_GlobalDiscountValue'] = discount_global_value

		discount = discount + discount_global_value

		""" Asignamos el valor al item """
		return discount

	def build_discount(self, item):
		""" Devuelve los descuentos """
		markup = '<SubDscto>'
		if 'DescuentoPct' in item:
			markup = markup + "<TipoDscto>%</TipoDscto>"
		else:
			markup = markup + "<TipoDscto>$</TipoDscto>"

		valor_discount = str(self._calculate_discount(item))
		markup = markup + "<ValorDscto>" + valor_discount + "</ValorDscto>"

		markup = markup + '</SubDscto>'
		""" Total descuento por el item """
		markup = "<DescuentoMonto>" + valor_discount + "</DescuentoMonto>" + markup
		return markup

	def calculated_field(self, field:str, item:Dict) -> str:
		""" Calculamos los campos dinamicos """
		total_item = ""
		if 'Credit' in item:
			""" Nota de credito, valor a creditar """
			total_item = int(item['Credit'])
		elif field == 'ItemPrice' or field =='ExentPrice':
			""" Precio del item """
			""" Según SII : (Precio Unitario * Cantidad ) – Monto Descuento + Monto Recargo  """
			discount = self._calculate_discount(item, False)
			if field =='ExentPrice':
				discount = 0
		elif field == 'TotalPrice':
			discount = self._calculate_discount(item)

		if 'Quantity' in item and 'UnitPrice' in item:
			total_item = int(item['Quantity']) * int(item['UnitPrice']) - discount
		else:
			total_item = 0 - discount

		total_item = int(round(total_item, 0))

		return total_item

	def get_totales(self, iva_rate:int) -> Dict:
		""" Calcula los totales """
		totales = {}
		totales['Net'] = 0
		totales['TotalExento'] = 0
		totales['TotalDiscounts'] = 0

		for item_key in self._items:
			current_item =  self._items[item_key]
			if 'UnitPrice' not in current_item:
				""" Mocked para los item sin precio unitario """
				current_item['UnitPrice'] = 1

			if 'UnitPrice' in current_item:
				""" If price is set """
				""" Calculate """
				total_item = self.calculated_field('TotalPrice', current_item)

				if 'Exento' in current_item:
					exent_type = int(current_item['Exento'])
					if exent_type > 0:
						""" 1 : No afecta, exento de IVA """
						totales['TotalExento'] = totales['TotalExento'] + total_item
					else:
						#raise ValueError("Indice de valor exenta invalido")
						""" Skip """
						print("Indice de valor exenta invalido")
				else:
					totales['Net'] = totales['Net'] + total_item

		totales['Rate'] = iva_rate
		totales['IVA'] = int(round(totales['Net'] * (iva_rate / 100)))
		totales['Total'] = int(round(totales['IVA'] + totales['Net'] + totales['TotalExento']))

		return totales

	def get_item_list_for_template(self):
		""" Calculamos los campos de totales """
		for k in self._items:
			item = self._items[k]
			if 'Quantity' in item and 'UnitPrice' in item:
				total_item = self.calculated_field('ItemPrice', item)
				item['ItemPrice'] = total_item

		return self._items

	def get_first_item_description(self):
		if len(self._items) > 0:
			first_key = list(self._items.keys())[0]
			description = ''
			try:
				description = self._items[first_key]['Description'][:40]
			except:
				description = self._items[first_key]['Name'][:40]

			""" Arreglo para el TED...."""
			description = sanitize_string(description)
			""" Pruena """
			description = description.replace('ó', 'o').replace('ñ', 'n')
			return description
		else:
			return ""

	def get_property_by_markup(self, document_type, search_markup):
		for property, markup in self.__properties_by_document_type[document_type].items():
			if markup == search_markup:
				return property
		""" Common properties """
		for property, markup in self.__properties_by_document_type[0].items():
			if markup == search_markup:
				return property

	def load_from_xml_parameters(self, document_type, parameters):
		self._items = {}
		index = 0
		for i in parameters:
			item = parameters[i]
			for elem in item:
				property = self.get_property_by_markup(document_type, elem)
				if property == "Index":
					index = item[elem]
					self._items[index] = {}
				if property is not None:
					self._items[index][property] = item[elem]

	def dump(self, skip_props=[]):
		if len(self._items) > 0:
			return self.dump_items(skip_props)
		else:
			return "<Detalle />"

class DTECover:

	"""
	<Caratula version="1.0">
		<RutEmisor>76087419-1</RutEmisor>
		<RutEnvia>22926257-2</RutEnvia>
		<RutReceptor>55555555-5</RutReceptor>
		<FchResol>2014-08-22</FchResol>
		<NroResol>80</NroResol>
		<TmstFirmaEnv>2020-03-19T11:22:45</TmstFirmaEnv>
		<SubTotDTE>
			<TpoDTE>110</TpoDTE>
			<NroDTE>1</NroDTE>
		</SubTotDTE>
	</Caratula>
	"""
	_dtes = {}
	""" Resolution must be {'Date':'YYYY-MM-DD', 'Number': 'XXXX' } """
	_resolution = {}
	""" User must be {'RUT' : 'XXXXXXXX-X'} """
	_user = {}

	def __init__(self, dtes, resolution, user):
		self._dtes = dtes
		self._resolution = resolution
		self._user = user

	def dump(self):
		dumped = '<Caratula version="1.0">' + \
				"\r\n" + \
				self.sender() + \
				"\r\n" + \
				self.receiver() + \
				"\r\n" + \
				self.resolution() + \
				"\r\n" + \
				self.signature_date() + \
				"\r\n" + \
				self.dte_details() + '</Caratula>'
		return dumped

	def sender(self):
		return '<RutEmisor>' + self.dte_sender() + '</RutEmisor>\r\n' + \
				'<RutEnvia>' + self._user['RUT'] + '</RutEnvia>'

	""" El recibidor es el SII cuando utilizamos el metodo de upload,
	Debe ser el recibidor especificado cuando se lo enviamos por correo """
	def receiver(self):
		#return '<RutReceptor>' + "60803000-K" + '</RutReceptor>'
		return '<RutReceptor>' + self.dte_receiver() + '</RutReceptor>'

	def resolution(self):
		return '<FchResol>' + self._resolution['Date'] + '</FchResol>\r\n' + \
				'<NroResol>' + self._resolution['Number'] + '</NroResol>'

	def signature_date(self):
		return '<TmstFirmaEnv>' + datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT) + '</TmstFirmaEnv>'

	def dte_sender(self):
		sender = ''
		for dte in self._dtes:
			doc = self._dtes[dte]
			if sender == '':
				sender = doc.get_document_sender()
			else:
				if sender != doc.get_document_sender():
					raise ValueError('Multiple document sender found. Should be only one document sender by Set.')
		return sender

	def dte_receiver(self):
		receiver = ''
		for dte in self._dtes:
			doc = self._dtes[dte]
			if receiver == '':
				receiver = doc.get_document_receiver()
			else:
				if receiver != doc.get_document_receiver():
					raise ValueError('Multiple document receiver found. Should be only one document receiver by Set.')
		return receiver.replace("\r\n", "")

	def dte_details(self):
		quantity_by_type = {}
		""" Obtener cantidad de DTE por tipo """
		for dte in self._dtes:
			doc = self._dtes[dte]
			doc_type = doc.get_document_type()

			if doc_type not in quantity_by_type:
				quantity_by_type[doc_type] = 0
			quantity_by_type[doc_type] = quantity_by_type[doc_type] + 1

		sub_tot_dte_dump = ''

		for dte_type in quantity_by_type:
			sub_tot_dte_dump = sub_tot_dte_dump + '<SubTotDTE>' + "\r\n"
			sub_tot_dte_dump = sub_tot_dte_dump + "<TpoDTE>" + str(dte_type) + "</TpoDTE>" + "\r\n" + "<NroDTE>" + str(quantity_by_type[dte_type]) + "</NroDTE>"
			sub_tot_dte_dump = sub_tot_dte_dump + '</SubTotDTE>'

		return sub_tot_dte_dump

class DTECAF:
	embedded_private_key = ''
	_file_content = ''
	_parameters = None
	_signature = ''
	__markup = { 'RUT':'RE',
					'Name':'RS',
					'Type':'TD',
					'_From':'D',
					'_To':'H',
					'Range': 'RNG',
					'FechaAuthorization':'FA',
					'RSAPrivateKey': 'RSAPK',
					'_RSAPrivateKeyModule':'M',
					'_RSAPrivateKeyExp':'E',
					'KeyId':'IDK',
					'_Signature' :'',
					'_PrivateKey': '',
					'_EmbeddedSignature': 'FRMA',
					'_RSAPrivateKey': 'RSASK',
					'_RSAPublicKey': 'RSAPUBK'
					}
	algorithm = 'SHA1withRSA'
	def __name__(self):
		return 'DTECAF'

	def __init__(self, signature, parameters, private_key='', file_content=''):
		self._parameters = parameters
		self._signature = signature
		if('_RSAPrivateKey' in parameters):
			self.embedded_private_key = parameters['_RSAPrivateKey']
		else:
			self.embedded_private_key = private_key

	def dump(self):
		""" Para copiarlo tal cual como fue entregado """
		return self._file_content

	def _load_from_etree(self, tree_caf):
		""" Buscamos el <CAF> """
		caf_node = tree_caf.find("CAF")
		if not caf_node:
			""" Nullo, tal vez el archivo contiene solamente el node CAF """
			caf_node = tree_caf
		""" Lo guardamos """
		self._file_content = etree.tostring(caf_node, encoding='iso-8859-1').decode()
		""" Eliminamos la declaración XML """
		self._file_content = self._file_content.replace("<?xml version='1.0' encoding='iso-8859-1'?>", "")

		return self.load_from_etree(tree_caf)

	def load_from_XML(self, filepath):
		""" Load etree from file """
		tree = etree.parse(filepath)
		return self._load_from_etree(tree)

	def load_from_XML_string(self, xml_string):
		""" Load etree from string """
		tree = etree.fromstring(xml_string)
		return self._load_from_etree(tree)

	def get_property_by_markup(self, search_markup):
		for property, markup in self.__markup.items():
			if markup == search_markup:
				return property

	def load_from_etree(self, tree):
		""" Load from etree object """
		for elem in tree.iter():
			property = self.get_property_by_markup(elem.tag)
			if property is not None:
				self._parameters[property] = elem.text
			if property == 'Range':
				self._parameters[property] = {}
				""" Rango de folios """
				for rng_prop in elem.iter():
					if rng_prop.tag == 'D':
						""" Desde """
						self._parameters[property]['From'] = rng_prop.text
					elif rng_prop.tag == 'H':
						self._parameters[property]['Hasta'] = rng_prop.text
			""" Get signature algorithm """
			if elem.tag == 'FRMA':
				self.algorithm = elem.attrib['algoritmo']

		self.embedded_private_key = self._parameters['_RSAPrivateKey']

	def load_from_xml_parameters(self, parameters):
		""" Load from dictionnary of parameters [markup => value] """
		for elem in parameters:
			property = self.get_property_by_markup(elem)
			if property is not None:
				self._parameters[property] = parameters[elem]

	def get_document_type(self):
		""" Returns SII document type """
		return int(self._parameters['Type'])

	def get_caf_property(self, property_name):
		""" Returns SII document type """
		return self._parameters[property_name]

class DTE:
	""" Envio DTE """
	""" From documentation, every document should have this parts : """
	"""
	A:- Datos de encabezado: corresponden a la identificación del documento, información del emisor, información del receptor y monto total de la transacción.
	B:- Detalle por Ítem: En esta zona se debe detallar una línea por cada Ítem. Se debe detallar cantidad, valor, descuentos y recargos por ítem,  impuestos adicionales y valor neto. En el caso de la Liquidación-Factura, se detallan los datos de los documentos liquidados.
	C:- Descuentos y Recargos: Esta zona se utiliza para especificar descuentos o recargos que afectan al total del documento y que no se requiere especificar ítem a ítem.
	D:- Información de Referencia: En esta zona se deben detallar los documentos de referencia, por ejemplo se debe identificar la Guía de Despacho que se está facturando o la Factura que se está modificando con una Nota de crédito o de débito.
	E:- Comisiones y Otros Cargos: Obligatoria para Liquidación Factura y opcional para Factura de Compra y Nota de Crédito/Débito que corrijan operaciones relacionadas con Facturas de Compra.
	F:- Timbre Electrónico SII: Firma electrónica sobre la información representativa del documento para permitir la validación del documento impreso.
	G:- Fecha y hora de la firma electrónica H.- Firma Electrónica sobre toda la información anterior para garantizar la integridad del DTE enviado al SII
	"""
	_header = None
	_items = None
	_discount = [] #DTEDiscount
	_reference = [] #DTEReference
	_other_charges = [] #DTEItems()
	_sii_signature = None
	_timestamp = datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT)
	_caf = None
	_document_id = ''
	_ted = ''

	def __init__(self, header, items, discount, reference, other, signature, timestamp, caf=None, signer=None, ted=''):
		self._header = header
		self._items = items
		self._discount = discount
		self._reference = reference
		self._other_charges = other
		self._sii_signature = signature
		self._timestamp = timestamp
		self._caf = caf
		self._document_id = 'T' + str(self._header.dte_document_type) + 'I' + str(self._header.dte_document_number)
		self._signer = signer
		self._ted = ted

	def set_document_number(self, document_number:int):
		""" Seteamos el folio """
		self._header.dte_document_number = document_number
		""" Para forzar la generación """
		self._ted = ''

	def get_total_amount(self):
		return self._items.get_totales(19)['Total']

	def generate_ted(self):
		""" Generamos el TED """
		""" If not already generated """
		if self._header.dte_document_type == 52:
			self._header.totales['Total'] = 0

		if self._ted == '':
			caf_private_key = ''
			document_data = '<DD>\r\n' + \
					  '<RE>' + self._header.sender.get_attr('RUT') + '</RE>\r\n' + \
					  '<TD>' + str(self._header.dte_document_type) + '</TD>\r\n' + \
					  '<F>' + str(self._header.dte_document_number) + '</F>\r\n' + \
					  '<FE>' + str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT_SHORT)) + '</FE>\r\n' + \
					  '<RR>' + self._header.receiver.get_attr('RUT') + '</RR>\r\n' + \
					  '<RSR>' + sanitize_string(string=self._header.receiver.get_attr('Name'), size=40) + '</RSR>\r\n' + \
					  '<MNT>' + str(self._header.totales['Total']) + '</MNT>\r\n' + \
					  '<IT1>' + self._items.get_first_item_description() + '</IT1>\r\n' + \
					   self._caf.dump() + \
					  '<TSTED>' + str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT)) + '</TSTED>\r\n' + \
					  '</DD>'

			""" Se calcula la firma sobre lo que hay dentro del <TED> sin espacios/saltos/tabulación """
			flatten = document_data.replace('\b', '').replace('  ', '').replace('\t', '').replace('\r', '').replace('\n', '')

			signature = self.sign(flatten, self._caf.embedded_private_key, self._caf.algorithm)
			ted = '<TED version="1.0">' + \
				document_data + \
			  '<FRMT algoritmo="SHA1withRSA">' + signature + '</FRMT>' + \
			  '</TED>'

			self._ted = ted
			return ted
		else:
			return self._ted

	def get_document_type(self):
		return str(self._header.dte_document_type)

	def get_document_number(self):
		return self._header.dte_document_number

	def get_document_id(self):
		return str(self._document_id)

	def get_document_sender(self):
		return self._header.sender.get_attr('RUT')

	def get_document_receiver(self):
		return self._header.receiver.get_attr('RUT')

	def sign(self, data, key, algorithm='SHA1withRSA'):
		""" Sign document """
		""" If there a signer module loaded """
		if self._signer is not None:
			self._signer.key = key
			sign = self._signer.sign_with_algorithm(data, algorithm)
			return sign
		else:
			""" Sign """
			import xmlsec
			import base64
			ctx = xmlsec.SignatureContext()
			""" La clave no tiene que tener espacio """

			ctx.key = xmlsec.Key.from_memory(key.replace("        ",""), format=xmlsec.constants.KeyDataFormatPem)
			#ctx.key = xmlsec.Key.from_file("../client_ssl.pem",  xmlsec.constants.KeyDataFormatPem , "2022")

			data_bytes = data.encode('iso-8859-1')

			sign = ctx.sign_binary(data_bytes, xmlsec.constants.TransformRsaSha1)
			""" To base 64 and back """
			base64_encoded_data = base64.b64encode(sign)
			return base64_encoded_data.decode()

	def dump(self):
		return '<DTE version="1.0">' + \
		 		self.dump_document_only() + \
				build_signature(self.get_document_id()) + '</DTE>'

	def dump_document_only(self):
		ted = ''
		if self._ted == '':
			""" Generate """
			ted = self.generate_ted()
		else:
			""" Preloaded """
			ted = self._ted

		""" Referencias """
		references = ''
		if len(self._reference) > 0:
			for r in self._reference:
				references = references + r.dump()

		""" Descuentos """
		descuentos_globales = ''
		if len(self._discount) > 0:
			for d in self._discount:
				descuentos_globales = descuentos_globales + d.dump()

		""" Segun el tipo de documento, vamos a omitir algunas propriedades """
		skip_props = build_skippable_properties(self._header)

		return '<Documento ID="' + self._document_id + '">' + \
				self._header.dump() + \
				self._items.dump(skip_props) + \
				descuentos_globales + \
				references + \
				ted + \
				'<TmstFirma>' + \
				str(datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT)) + \
				'</TmstFirma></Documento>'

	def to_template_parameters(self):
		references_template = {}
		if self._reference and len(self._reference) > 0:
			index = 0
			for k in self._reference:
				references_template[index] = k._parameters
				index = index + 1

		discounts_template = {}
		if self._discount and len(self._discount) > 0:
			index = 0
			for k in self._discount:
				discounts_template[index] = k._parameters
				index = index + 1

		dict = {
				'Header': {
					'Specifics': self._header.get_specifics_for_display(),
					'IssuedDate': self._header.get_issue_date(),
					'LimitDate': self._header.get_expiry_date()
				},
				'Sender': {
							'RUT':self._header.sender.get_attr('RUT'),
							'Name':self._header.sender.get_attr('Name'),
							'Activity':self._header.sender.get_attr('Activity'),
							'Address':self._header.sender.get_attr('Address'),
							'Address2':'',
							'City':self._header.sender.get_attr('City'),
							'Phone':self._header.sender.get_attr('Phone'),
							'Contact': self._header.sender.get_attr('Contact')
							},
				'DocumentNumber': self._header.dte_document_number,
				'SII' : 'SANTIAGO CENTRO',
				'Receiver': {
							'RUT':self._header.receiver.get_attr('RUT'),
							'Name':self._header.receiver.get_attr('Name'),
							'Activity':self._header.receiver.get_attr('Activity'),
							'Address':self._header.receiver.get_attr('Address'),
							'Address2':'',
							'City':self._header.receiver.get_attr('City'),
							'State':self._header.receiver.get_attr('State'),
							'Phone':self._header.receiver.get_attr('Phone'),
							'Contact': self._header.receiver.get_attr('Contact'),
							'Email': self._header.receiver.get_attr('Email')
				},
				'Details': self._items.get_item_list_for_template(),
				'References': references_template,
				'Discounts': discounts_template,
				'Comment': self._header.comment,
				'Totales': self._header.totales
		}

		return dict

class DTEPayload:
	""" EnvioDTE """
	_set_id = ''
	def __init__(self, dtes, cover, user, set_id='SetDoc'):
		self._dtes = dtes
		self._cover = cover
		self._set_id = set_id

	def dump(self):
		dumped = self.dump_without_xml_declaration()
		dumped = '<?xml version="1.0" encoding="ISO-8859-1"?>' + dumped

		return dumped

	def dump_without_xml_declaration(self):
		set = '<SetDTE ID="' + self._set_id + '">' + \
				self._cover.dump() + \
				self.dump_documents() + '</SetDTE>'
		dumped = '<EnvioDTE xmlns="http://www.sii.cl/SiiDte" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.sii.cl/SiiDte EnvioDTE_v10.xsd" version="1.0">' + \
			 set + build_signature(self._set_id) + '</EnvioDTE>'

		return dumped

	def dump_documents(self):
		dumped = ''
		for doc in self._dtes:
			dumped = dumped + self._dtes[doc].dump()

		return dumped

class DTEBuidler:
	__iva_by_type = {33: 19, 52: 19, 34: 0}
	__object_type_by_tag = { '{http://www.sii.cl/SiiDte}RutEmisor':'RE',
					'Name':'RS',
					'Type':'TD',
					'_From':'D',
					'_To':'H',
					'FechaAuthorization':'FA',
					'_RSAPrivateKeyModule':'M',
					'_RSAPrivateKeyExp':'E',
					'KeyId':'IDK',
					'_Signature' :'',
					'_PrivateKey': '',
					'_EmbeddedSignature': 'FRMA',
					'_RSAPrivateKey': 'RSASK',
					'_RSAPublicKey': 'RSAPUBK'
					}

	def _get_iva_by_document_type(self, type):
		try:
			return self.__iva_by_type[type]
		except:
			print("_get_iva_by_document_type:: IVA not defined for document type " + str(type))
			print("_get_iva_by_document_type:: Return default 19%")
			return 19

	def build(self, type, sender, receiver, header, items, references, discounts, caf):
		sender_object = DTEPerson(1, sender)
		receiver_object = DTEPerson(0, receiver)

		""" Load references """
		references_object = []
		for r in references:
			reference = references[r]
			new_reference = DTEReference(reference)
			references_object.append(new_reference)

		""" Load discounts """
		discounts_object = []
		for d in discounts:
			discount = discounts[r]
			new_discount = DTEDiscount(discount)
			discounts_object.append(new_discount)

		""" Pasar descuentos a los items para recalcular """
		items_object = DTEItems(type, items, {'global_discounts': discounts_object})

		iva_rate = self._get_iva_by_document_type(type)

		header_object = DTEHeader(sender=sender_object, receiver=receiver_object, document_type=type, \
									document_number=header['DocumentNumber'], payment_method=header['PaymentType'], expiry_date=header['ExpiryDate'], \
									specific_parameters=header, totales=items_object.get_totales(iva_rate))

		if isinstance(caf, DTECAF):
			""" Is already an object """
			caf_object = caf
		else:
			""" Build object """
			caf_object = DTECAF(parameters=caf, signature=signature, private_key=private_key)
			signature = caf['_Signature']
			private_key = caf['_PrivateKey']

		dte = DTE(header_object, items_object, discounts_object, references_object, '', '', '',caf=caf_object)

		dte_dump = dte.dump()

		dte_etree = etree.fromstring(dte_dump)
		pretty_dte = etree.tostring(dte_etree, pretty_print=False).decode('iso-8859-1')
		return dte_etree, pretty_dte, dte

	def from_file(self, path):
		tree = etree.parse(path)
		root = tree.getroot()

		return self.load_from_etree(root)

	def from_string(self, string):
		root = etree.fromstring(string)

		return self.load_from_etree(root)

	def iterate_recurs_etree(self, tree, parameters):
		items = 0

		if not tree:
			return parameters
		for child in tree:
			""" Remove SII general tag """
			""" Could be comment too, in this case we skip """
			if isinstance(child.tag, str):
				tag = child.tag.replace('{http://www.sii.cl/SiiDte}','')

				if len(child) > 1:
					""" Extract elements """
					if tag == 'Encabezado':
						header = {}
						parameters['Header'] = {}
						parameters['Header'] = self.iterate_recurs_etree(child, header)
					if tag == 'Caratula':
						""" Specific headers """
						spec = {}
						parameters['User'] = {}
						parameters['User'] = self.iterate_recurs_etree(child, spec)
					if tag == 'Emisor':
						sender = {}
						parameters['Sender'] = {}
						parameters['Sender'] = self.iterate_recurs_etree(child, sender)
					if tag == 'Receptor':
						receiver = {}
						parameters['Receiver'] = {}
						parameters['Receiver'] = self.iterate_recurs_etree(child, receiver)
					if tag == 'Detalle':
						item = {}
						if 'Items' not in parameters:
							items = 0
							parameters['Items'] = {}
						parameters['Items'][items] = {}
						parameters['Items'][items] = self.iterate_recurs_etree(child, item)
						items = items + 1
					if tag == 'Referencia':
						item = {}
						if 'References' not in parameters:
							items = 0
							parameters['References'] = {}
						parameters['References'][items] = {}
						parameters['References'][items] = self.iterate_recurs_etree(child, item)
						items = items + 1
					if tag == 'DscRcgGlobal':
						item = {}
						if 'Discounts' not in parameters:
							items = 0
							parameters['Discounts'] = {}
						parameters['Discounts'][items] = {}
						parameters['Discounts'][items] = self.iterate_recurs_etree(child, item)
						items = items + 1
					if tag == 'CAF':
						caf = {}
						parameters['CAF'] = {}
						parameters['CAF'] = self.iterate_recurs_etree(child, caf)
					if tag == 'TED':
						ted = {}
						parameters['TED'] = {}
						parameters['TED'] = self.iterate_recurs_etree(child, ted)
						parameters['TED']['Dump'] = etree.tostring(child).decode('UTF-8')
					if tag == 'Totales':
						totals = {}
						parameters['Totals'] = {}
						parameters['Totals'] = self.iterate_recurs_etree(child, totals)
					else:
						self.iterate_recurs_etree(child, parameters)
				else:
					if tag == "TpoDocRef":
						""" Specific, convert document type to human readable """
						try:
							parameters[tag] = child.text + "-" +  db_codes['Description']['ReferenceType'][child.text]
						except:
							parameters[tag] = child.text + "-ND"
					else:
						parameters[tag] = child.text

		return parameters

	def load_from_etree(self, tree):
		""" Build parameters """
		DET_NODE = "{http://www.sii.cl/SiiDte}DTE"
		DET_PAYLOAD = "{http://www.sii.cl/SiiDte}SetDTE"

		parameters = {}
		dtes = [d for d in tree.iter(DET_NODE)]
		k =  0
		""" Cargamos el encabezado del envío """
		payload_header = {}
		payload_header = self.iterate_recurs_etree(tree.find(DET_PAYLOAD), payload_header)
		""" Cargamos cada DTE individualmente """
		for node in dtes:
			parameters[k] = {}
			parameters[k] = self.iterate_recurs_etree(node, parameters[k])

			k = k + 1

		""" Recuperamos elementos de firma, alojado en el doc 0 (encabezado) """
		payload_header['Signature'] = {}
		for k in payload_header:
			if k.startswith('{http://www.w3.org/2000/09/xmldsig#}'):
				tag = k.replace('{http://www.w3.org/2000/09/xmldsig#}', '')
				payload_header['Signature'][tag] = payload_header[k]

		""" Get individual set """
		documents = []

		for k in parameters:
			doc_parameters = parameters[k]
			doc_parameters['Signature'] = {}
			for e in doc_parameters:
				if e.startswith('{http://www.w3.org/2000/09/xmldsig#}'):
					tag = e.replace('{http://www.w3.org/2000/09/xmldsig#}', '')
					doc_parameters['Signature'][tag] = doc_parameters[e]

			""" Para cada documento, generar el objeto DTE """
			sender_parameters = doc_parameters['Sender']
			receiver_parameters = doc_parameters['Receiver']
			items_parameters = doc_parameters['Items']
			caf_parameters = doc_parameters['CAF']
			ted_parameters = doc_parameters['TED']
			""" Contains sender RUT, Resolution parameters, usually provided throught authentication """
			miscs = payload_header['User']
			header_parameters = doc_parameters['Header']

			for prop in miscs:
				header_parameters[prop] = miscs[prop]

			if 'Discounts' not in doc_parameters:
				doc_parameters['Discounts'] = []
			else:
				discount_list = []
				for k in doc_parameters['Discounts']:
					discount_object = DTEDiscount({})
					discount_object.from_xml_tags(doc_parameters['Discounts'][k])
					discount_list.append(discount_object)
				doc_parameters['Discounts'] = discount_list

			if 'References' not in doc_parameters:
				doc_parameters['References'] = []
			else:
				reference_list = []
				for k in doc_parameters['References']:
					reference_object = DTEReference({})
					reference_object.from_xml_tags(doc_parameters['References'][k])
					reference_list.append(reference_object)
				doc_parameters['References'] = reference_list

			""" Get dumped TED """
			dumped_ted = doc_parameters['TED']['Dump']
			""" Totals """
			totals_parameters = doc_parameters['Totals']

			""" Build objects """
			""" Send and receiver """
			sender = DTEPerson(1, None)
			sender.from_xml_parameters(1, sender_parameters)
			receiver = DTEPerson(0, None)
			receiver.from_xml_parameters(0, receiver_parameters)
			""" CAF """
			caf = DTECAF(parameters={}, signature='', private_key='')
			caf.load_from_xml_parameters(caf_parameters)
			""" Get document type """
			document_type = caf.get_document_type()
			document_number = int(ted_parameters['F'])

			""" Items """
			if len(doc_parameters['Discounts']) == 1:
				items = DTEItems(document_type=document_type, items={}, args={'global_discounts':doc_parameters['Discounts']})
			else:
				items = DTEItems(document_type=document_type, items={})
			items.load_from_xml_parameters(document_type=document_type, parameters=items_parameters)
			""" Get IVA rate """
			iva_rate = self._get_iva_by_document_type(document_type)

			""" Build header """
			header = DTEHeader(sender, receiver, document_type, document_number, 1, datetime.datetime.now().strftime(DTE_SII_DATE_FORMAT), {}, items.get_totales(iva_rate))
			header.load_specifics_from_xml_parameters(document_type, header_parameters)

			""" Build final DTE """
			dte = DTE(header, items, discount=doc_parameters['Discounts'], reference=doc_parameters['References'], other='', signature=doc_parameters['Signature'], timestamp='',caf=caf, ted=dumped_ted)
			""" Extract tree and dump pretty XML """
			dte_etree = etree.fromstring(dte.dump())
			pretty_dte = etree.tostring(dte_etree, pretty_print=False).decode('UTF-8')

			documents.append((dte_etree, pretty_dte, dte))
		return payload_header, documents
