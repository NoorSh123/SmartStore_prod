from flask import jsonify, request


def json_object():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "A JSON object is required"}), 400)
    return data, None


def positive_int(value):
    return type(value) is int and value > 0
