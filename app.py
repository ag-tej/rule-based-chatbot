from flask import Flask, render_template, request, jsonify
from chat import get_response

app = Flask(__name__)

@app.get("/")
def index_get() -> str:
  return render_template("base.html")

@app.post("/predict")
def predict() -> jsonify:
  if not request.is_json:
    return jsonify({"error": "Invalid content type, JSON required"}), 400
  query = request.get_json().get("message")
  if not query:
    return jsonify({"error": "Query is required"}), 400
  response = get_response(query)
  message = {"answer": response}
  return jsonify(message)

if __name__ == "__main__":
  app.run(debug=True)
