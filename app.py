from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(status="ok")


@app.get("/add")
def add():
    try:
        a = int(request.args.get("a", ""))
        b = int(request.args.get("b", ""))
    except ValueError:
        return jsonify(error="a and b must be integers"), 400
    return jsonify(result=a + b)
