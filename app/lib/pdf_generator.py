"""

 Generate PDFs

 Needed : sudo apt install -y wkhtmltopdf
 Or Windows: https://wkhtmltopdf.org/downloads.html

"""

import pdfkit
import pdf417
import os
import os.path
from lib.models.dte import DTE, DTEBuidler, DTECAF
from jinja2 import Environment, FileSystemLoader
from instance.config import WKHTMLTOPDF_EXE_PATH
from instance.config import APP_ROOT

FILE_DIR = os.path.dirname(os.path.realpath(__file__))

WKHTMLTOPDF_OPTIONS = {
			'page-size': 'A3',
			'dpi': 600,
			'enable-local-file-access': None,
			'load-error-handling': 'ignore'
		}

class PDFGenerator:
	""" Path to wkhtmltopdf """
	if len(WKHTMLTOPDF_EXE_PATH) > 0:
		__config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_EXE_PATH)
	else:
		__config = pdfkit.configuration()
	__template_by_type = {						
							33:'web/templates/sii_document_33.html',
							34:'web/templates/sii_document_34.html',
							46:'web/templates/sii_document_46.html',
							52:'web/templates/sii_document_52.html',
							56:'web/templates/sii_document_56.html',
							61:'web/templates/sii_document_61.html',
							110:'web/templates/sii_document_110.html',
							111:'web/templates/sii_document_111.html',
							112:'web/templates/sii_document_112.html'
						}

	def generate(self, dte, output_path="", filename="", cedible=False, template_parameters=None):
		# Use False instead of output path to save pdf to a variable
		ted = self._generate_png_ted(dte.get_document_id(), dte.generate_ted())
		html = self._populate_jinja_template(dte, ted, cedible, template_parameters)
		options = WKHTMLTOPDF_OPTIONS

		if filename == "":
			if cedible:
				filename = str(dte.get_document_id()) + '_CED' + '.pdf'
			else:
				filename = str(dte.get_document_id()) + '.pdf'

		if output_path == "":
			output_path = FILE_DIR + '/../temp/'

		fullpath = output_path + filename

		pdf = pdfkit.from_string(html, fullpath, options=options, configuration=self.__config)
		return filename

	def generate_binary(self, dte, cedible=False, template_parameters=None, preview=1):
		""" Genera el PDF correspondiente al DTE y lo almacena en una variable """
		""" Recuperamos el TED """
		ted = self._generate_png_ted(dte.get_document_id(), dte.generate_ted())
		""" Recuperamos el template jinja poblado """
		html = self._populate_jinja_template(dte, ted, cedible, preview, template_parameters)
		options = WKHTMLTOPDF_OPTIONS

		filename = str(dte.get_document_id()) + '.pdf'
		""" None como ruta de archivo para tener el pdf en una variable """
		pdf = pdfkit.from_string(html, None, options=options, configuration=self.__config)
		return filename, pdf

	def _populate_jinja_template(self, dte, ted, cedible=False, preview=1, template_parameters=None):
		""" Get template path by type """
		document_type = dte.get_document_type()

		try:
			template_path = self.__template_by_type[int(document_type)]
		except:
			print("_populate_jinja_template:: Template not declared for document type " + str(document_type) + " using 33 by default.")
			template_path = self.__template_by_type[33]

		with open(template_path, encoding="utf-8") as f:
			template_str = f.read()
		""" Load template """
		""" Normalize template """
		template_path = os.path.normpath(FILE_DIR + '/web/templates')
		temp_path = os.path.normpath(FILE_DIR + '/../temp')
		template = Environment(loader=FileSystemLoader([template_path, temp_path])).from_string(template_str)
		""" Get template parameters """
		if not template_parameters:
			template_parameters = dte.to_template_parameters()

		""" Render """
		try:
			html_str = template.render(parameters=template_parameters, ted=ted, cedible=cedible, preview=preview)
		except Exception as e:
			print("_populate_jinja_template:: Error while rendering template " + str(document_type) + ". Returning empty HTML.")
			print(str(e))
			html_str = "<div></div>"

		return html_str

	def _generate_svg_ted(self, ted_string):
		codes = pdf417.encode(ted_string, security_level=5)
		svg = pdf417.render_svg(codes, scale=3, ratio=3)  # ElementTree object
		return svg

	def generate_test_svg_ted(self, ted_string, filepath=FILE_DIR + '/../temp/test.svg'):
		unique = 1
		filename = str(unique) + 'barcode.svg'
		filepath = FILE_DIR + '/../temp/' + filename
		codes = pdf417.encode(ted_string, security_level=5)
		svg = pdf417.render_svg(codes, scale=3, ratio=3)  # ElementTree object
		svg.write(filepath)
		return filename

	def _generate_png_ted(self, document_id, ted_string):
		""" Guarda la imagen correspondiente al TED """
		filename = document_id + '-ted.png'
		filepath = FILE_DIR + '/../temp/' + filename
		filepath = os.path.normpath(filepath)
		""" Flatten """
		ted_string = ted_string.replace('\n', '')
		""" Generamos el imagen """
		print("KK", filename, ted_string)
		codes = pdf417.encode(ted_string, columns=10, security_level=5)
		image = pdf417.render_image(codes, scale=3, ratio=3, padding=5)  # Pillow Image object
		image.save(filepath)
		return filepath
