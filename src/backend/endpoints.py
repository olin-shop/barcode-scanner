from flask import Flask, jsonify, request, Response
from backend.backend_constants import CHECKOUT_URL, ITEM_URL, NAME_URL

flask_app: Flask = Flask(__name__)

# request.get_json()
# request.method == "POST"


@flask_app.route("/checkout", methods=["POST"])
def checkout() -> Response:
    return jsonify([])


@flask_app.route("/items", methods=["POST"])
def get_item() -> Response:
    return jsonify([])


@flask_app.route("/names", methods=["POST"])
def get_name() -> Response:
    return jsonify([])
