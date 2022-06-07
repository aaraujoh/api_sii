from flask import Flask, request, abort, jsonify

from .mysii import *
import base64

app = Flask(__name__)

APP_PATH="."

@app.route("/upload", methods=["POST"])
def upload():
    try:
        app.logger.debug(f"REQUEST {request.json}")
        data = request.json
        data["caf"] = base64.b64decode(data["caf"]).decode("utf-8")
        data["config"]["pem"] = base64.b64decode(data["config"]["pem"]).decode("utf-8")
        return jsonify(upload_xml(request.json))
    except Exception as e:
        app.logger.error(f"{e}")
        return jsonify(error="500", message=f"{str(e)}"), 500


@app.route("/check/<trackid>", methods=["GET"])
def chek(trackid):
    return {"status":0}