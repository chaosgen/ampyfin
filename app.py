from flask import Flask, render_template
from pymongo import MongoClient
from config import MONGO_DB_USER, MONGO_DB_PASS

app = Flask(__name__)

# MongoDB connection string
mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&writeConcern=majority"
mongo_client = MongoClient(mongo_url)
db = mongo_client.assets  # Change this if your database is named differently

@app.route('/')
def index():
    
    # Retrieve holdings
    holdings = db.asset_quantities.find()  # Adjust according to your collection name
    
    

    return render_template('index.html', holdings=holdings)

if __name__ == '__main__':
    app.run(debug=True)
