""" Template file, to be renamed to config.py """
# FLASK_LISTEN_PORT = "5001"
# FLASK_ENDPOINT = "127.0.0.1"
# DEBUG_MODE = True
# """ En DRY_RUN no enviamos información al SII, solamente firmamos etc. """
# DRY_RUN = True
""" Parametros de ruta """
""" Ruta hasta openssl """
#OPENSSL_PATH = r"C:\Program Files\Git\mingw64\bin\openssl.exe"
OPENSSL_PATH = r"/sw/anaconda/envs/fenix/bin/openssl"
""" Raiz del proyecto (para generar archivos temporario) """
APP_PATH = r"."
APP_ROOT = ""
""" Nombre de la aplicación emisora """
# APPLICATION_NAME = "DAIAERP"
""" Ruta del sitio web de la aplicación emisora """
REFERER = "https://daia.cl"

""" Ruta de WKHTML, para convertir documentos HTML en PDF (impresión del DTE) """
#WKHTMLTOPDF_EXE_PATH = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
WKHTMLTOPDF_EXE_PATH = r"/usr/bin/wkhtmltopdf"
# """ Parametros para poder leer correos que recibe y envia DTE """
# SII_INBOX_EMAIL_SERVER = ""
# SII_INBOX_EMAIL_ACCOUNT = ""
# SII_INBOX_EMAIL_PASSWORD = ""
# """ Criteria para filtrar los DTE recibidos """
# SII_INBOX_IMAP_CRITERIA = 'NOT SUBJECT "Resultado de Revision" RECENT'
# JSON_LAST_SEEN_PATH = "last_seen.json"
#
# """ Cadena de conexión a base de datos """
# SQL_ALCHEMY_DATABASE_OPTION = {'database': 'sii_dte'}
# #SQL_ALCHEMY_DATABASE_URI= "mssql://sii:sii@sii-SERVER/sii_dte?driver=SQL+Server+Native+Client+11.0"
# #SQL_ALCHEMY_TEST_DATABASE_URI = "mssql://localhost\SQLEXPRESS/sii_dte_test?driver=SQL+Server+Native+Client+11.0"
#
# SQL_ALCHEMY_DATABASE_URI= "sqlite:///sii_dte.db"
# #SQL_ALCHEMY_TEST_DATABASE_URI = "mssql://localhost\SQLEXPRESS/sii_dte_test?driver=SQL+Server+Native+Client+11.0"
#
#
# DEBUG_MODE=True


