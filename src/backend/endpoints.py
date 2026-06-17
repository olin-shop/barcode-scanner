from flask import Flask, jsonify, request, Response

flask_app: Flask = Flask(__name__)

# request.get_json()
# request.method == "POST"


@flask_app.route("/checkout", methods=["POST"])
def checkout() -> Response:
    """
    The checkout route.

    When this endpoint is accessed, it will be receiving data
    from the checkout pipeline in our databases.
    """
    return jsonify([])


@flask_app.route("/items", methods=["POST"])
def get_item() -> Response:
    """
    The item route.

    When this endpoint is accessed, it will be receiving the item
    data that was requested.
    """
    return jsonify([])


@flask_app.route("/names", methods=["POST"])
def get_name() -> Response:
    """
    The name route.

    When this endpoint is accessed, it will be receiving the first name,
    last name and email from a previous request.
    """
    return jsonify([])


@flask_app.route("/borrowed-items", methods=["POST"])
def request_borrowed_items() -> Response:
    """
    The borrowed items route.

    When this endpoint is accessed, it will be receiving the user info
    for all of the items that are currently borrowed, for reminder
    purposes.
    """
    return jsonify([])
