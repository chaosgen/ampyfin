from flask import Flask, render_template
from pymongo import MongoClient
import os

app = Flask(__name__)

# MongoDB connection string using environment variables
mongo_user = os.environ.get('MONGO_DB_USER')
mongo_pass = os.environ.get('MONGO_DB_PASS')
mongo_url = f"mongodb+srv://{mongo_user}:{mongo_pass}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"

mongo_client = MongoClient(mongo_url)
db = mongo_client.assets  # Change this if your database is named differently

@app.route('/')
def index():
    # Retrieve holdings
    holdings = list(db.asset_quantities.find())  # Convert to list to pass to template
    
    return render_template('index.html', holdings=holdings)

if __name__ == '__main__':
    app.run(debug=True)

