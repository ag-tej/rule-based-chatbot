from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from chat import get_response
from pymongo import MongoClient
from datetime import datetime
import json
import torch
from train import train_model
from bson import ObjectId

app = Flask(__name__)
app.secret_key = 'b30486c9c3cf11c1fd78d015bd1055b0c8429385544213ed1514558ba78603d9'

# Hardcoded credentials
CREDENTIALS = {
    'admin': 'password123'
}

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['chatbot']
unknown_queries = db['unknown_queries']
intents_collection = db['intents']

def login_required(func):
    """Decorator to protect routes."""
    def wrapper(*args, **kwargs):
        if not session.get('logged_in'):
            return redirect(url_for('login_get'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@app.get("/")
def index_get() -> str:
    return render_template("base.html")

@app.get("/login")
def login_get() -> str:
    return render_template("login.html")

@app.post("/login")
def login_post() -> str:
    username = request.form.get('username')
    password = request.form.get('password')
    if CREDENTIALS.get(username) == password:
        session['logged_in'] = True
        session['username'] = username
        return redirect(url_for('admin_get'))
    return render_template("login.html", error="Invalid username or password")

@app.get("/logout")
def logout_get() -> str:
    session.clear()
    return redirect(url_for('login_get'))

@app.get("/admin")
@login_required
def admin_get() -> str:
    return render_template("admin.html")

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

@app.route('/api/unknown-queries', methods=['GET', 'POST', 'DELETE'])
@login_required
def handle_unknown_queries():
    if request.method == 'POST':
        query = request.json.get('query')
        if not query:
            return jsonify({"error": "Query is required"}), 400
        
        unknown_queries.insert_one({
            'query': query,
            'timestamp': datetime.utcnow(),
            'status': 'pending'
        })
        return jsonify({"message": "Query recorded successfully"})
    
    elif request.method == 'DELETE':
        query_id = request.json.get('id')
        if not query_id:
            return jsonify({"error": "Query ID is required"}), 400
        
        unknown_queries.delete_one({'_id': ObjectId(query_id)})
        return jsonify({"message": "Query deleted successfully"})

    # GET method
    queries = list(unknown_queries.find())
    for query in queries:
        query['_id'] = str(query['_id'])
        query['timestamp'] = query['timestamp'].isoformat()
    return jsonify(queries)

@app.route('/api/intents', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def handle_intents():
    if request.method == 'GET':
        intents = list(intents_collection.find())
        for intent in intents:
            intent['_id'] = str(intent['_id'])
        return jsonify(intents)
    
    elif request.method == 'POST':
        intent = request.json.get('intent')
        query_id = request.json.get('queryId')
        
        if not intent or 'tag' not in intent or 'patterns' not in intent or 'responses' not in intent:
            return jsonify({"error": "Invalid intent format. Required keys: tag, patterns, responses"}), 400
        
        # Check for duplicate tags
        with open('intents.json', 'r') as f:
            intents_data = json.load(f)
        
        if any(existing_intent['tag'] == intent['tag'] for existing_intent in intents_data['intents']):
            return jsonify({"error": f"Intent with tag '{intent['tag']}' already exists."}), 400
        
        # Append new intent
        intents_data['intents'].append(intent)
        
        # Save to JSON file
        with open('intents.json', 'w') as f:
            json.dump(intents_data, f, indent=2, ensure_ascii=False)
        
        # Update MongoDB if necessary
        intents_collection.insert_one(intent)
        
        # Update query status
        if query_id:
            unknown_queries.update_one(
                {'_id': ObjectId(query_id)},
                {'$set': {'status': 'answered'}}
            )
        
        # Retrain model
        train_model()
        
        return jsonify({"message": "Intent added and model retrained successfully"})
    
    elif request.method == 'PUT':
        intent_id = request.json.get('id')
        updated_intent = request.json.get('intent')
        
        if not intent_id or not updated_intent or 'tag' not in updated_intent:
            return jsonify({"error": "Intent ID and valid updated intent are required"}), 400
        
        # Remove _id field if it exists
        updated_intent.pop('_id', None)
        
        # Update MongoDB
        intents_collection.update_one(
            {'_id': ObjectId(intent_id)},
            {'$set': updated_intent}
        )
        
        # Update intents.json
        with open('intents.json', 'r') as f:
            intents_data = json.load(f)
        
        for i, intent in enumerate(intents_data['intents']):
            if intent.get('tag') == updated_intent['tag']:
                intents_data['intents'][i] = updated_intent
                break
        
        with open('intents.json', 'w') as f:
            json.dump(intents_data, f, indent=2, ensure_ascii=False)
        
        # Retrain model
        train_model()
        
        return jsonify({"message": "Intent updated and model retrained successfully"})
    
    elif request.method == 'DELETE':
        intent_id = request.json.get('id')
        tag = request.json.get('tag')
        
        if not intent_id or not tag:
            return jsonify({"error": "Intent ID and tag are required"}), 400
        
        # Delete from MongoDB
        intents_collection.delete_one({'_id': ObjectId(intent_id)})
        
        # Update intents.json
        with open('intents.json', 'r') as f:
            intents_data = json.load(f)
        
        intents_data['intents'] = [i for i in intents_data['intents'] if i['tag'] != tag]
        
        with open('intents.json', 'w') as f:
            json.dump(intents_data, f, indent=2, ensure_ascii=False)
        
        # Retrain model
        train_model()
        
        return jsonify({"message": "Intent deleted and model retrained successfully"})

if __name__ == "__main__":
    app.run(debug=True)
