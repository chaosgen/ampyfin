from flask import Flask, render_template, jsonify
from pymongo import MongoClient
import os

app = Flask(__name__)

# MongoDB connection string using environment variables
mongo_url = f"mongodb+srv://{os.environ['MONGO_DB_USER']}:{os.environ['MONGO_DB_PASS']}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"
mongo_client = MongoClient(mongo_url)
db = mongo_client.assets  # Change this if your database is named differently

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/holdings')
def get_holdings():
    holdings = list(db.asset_quantities.find())
    return jsonify(holdings)

if __name__ == '__main__':
    app.run(debug=True)
