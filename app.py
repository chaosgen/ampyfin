import os
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List
from bson import ObjectId
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# FastAPI app initialization
app = FastAPI()

# MongoDB credentials from environment variables - use the config for testing purpose
"""
from config import MONGO_DB_USER, MONGO_DB_PASS
"""

MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASS = os.getenv("MONGO_DB_PASS")

MONGODB_URL = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&w=majority"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)

# Access the database and collections
try:
    # For holdings collection
    db = client.get_database("trades")
    holdings_collection = db.get_collection("assets_quantities")

    # For rankings collection (if needed)
    db = client.get_database("trading_simulator")
    rankings_collection = db.get_collection("rank")
    
    print("MongoDB collections are connected and ready.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# Pydantic model for holdings (symbol and quantity only)
class HoldingModel(BaseModel):
    id: str
    symbol: str
    quantity: float

    class Config:
        json_encoders = {ObjectId: str}  # Ensure ObjectId is converted to string

# Pydantic model for rankings (strategy and rank)
class RankingModel(BaseModel):
    id: str
    strategy: str
    rank: int

    class Config:
        json_encoders = {ObjectId: str}  # Ensure ObjectId is converted to string

@app.get("/holdings", response_model=List[HoldingModel])
async def get_holdings():
    """
    Fetch all the current holdings from the database.
    """
    holdings = []
    try:
        holdings_doc = await holdings_collection.find({}).to_list(length=100)
        for holding_doc in holdings_doc:
            holding = {
                "id": str(holding_doc["_id"]),
                "symbol": holding_doc.get("symbol", "None"),
                "quantity": holding_doc.get("quantity", 0)
            }
            holdings.append(holding)
    except Exception as e:
        print(f"Error fetching holdings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch holdings")
    
    return holdings

@app.get("/rankings", response_model=List[RankingModel])
async def get_rankings():
    """
    Fetch algorithm rankings from the database.
    """
    rankings = []
    try:
        rankings_doc = await rankings_collection.find({}).sort("rank", 1).to_list(length=100)  # Sorting by rank
        for ranking_doc in rankings_doc:
            ranking = {
                "id": str(ranking_doc["_id"]),
                "strategy": ranking_doc.get("strategy", "Unknown Strategy"),
                "rank": ranking_doc.get("rank", 0)
            }
            rankings.append(ranking)
    except Exception as e:
        print(f"Error fetching rankings: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch rankings")
    
    return rankings

@app.get("/")
async def root():
    """
    A simple route to verify the API is running.
    """
    return {"message": "AmpyFin API is running!"}
