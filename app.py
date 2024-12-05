import os
from fastapi import FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel
from typing import List, Dict, Optional
from bson import ObjectId
from fastapi.middleware.cors import CORSMiddleware
from strategies.trading_strategies_v1 import get_historical_data
from dotenv import load_dotenv
from statistics import median
from alpaca.data.historical.stock import StockHistoricalDataClient
# Custom helper methods
from helper_files.client_helper import strategies, get_latest_price

load_dotenv()
# FastAPI app initialization
app = FastAPI()

# MongoDB credentials from environment variables (imported from config)


MONGO_DB_USER = os.getenv("MONGO_DB_USER")
MONGO_DB_PASS = os.getenv("MONGO_DB_PASS")
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

"""
comment out when uploading for change

from config import MONGO_DB_USER, MONGO_DB_PASS, API_KEY, API_SECRET
"""


MONGODB_URL = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net/?retryWrites=true&w=majority"

# Initialize MongoDB client
client = AsyncIOMotorClient(MONGODB_URL)
data_client = StockHistoricalDataClient(API_KEY, API_SECRET)
# Access the database and collections
try:
    db = client.get_database("trades")
    holdings_collection = db.get_collection("assets_quantities")
    portfolio_value_collection = db.get_collection("portfolio_value")

    db = client.get_database("trading_simulator")
    rankings_collection = db.get_collection("rank")
    rank_to_coefficent_collection = db.get_collection("rank_to_coefficient")
    print("MongoDB collections are connected and ready.")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

# CORS configuration to allow frontend access (e.g., from a different domain)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can specify the domain if you have one (e.g., ["http://127.0.0.1:8001"])
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    rankings = []
    try:
        rankings_doc = await rankings_collection.find({}).sort("rank", 1).to_list(length=100)
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
@app.get("/portfolio_percentage")
async def get_portfolio_percentage():
    try:
        # Fetch all documents from the portfolio_value collection
        portfolio = await portfolio_value_collection.find({}).to_list(length=3)

        # Initialize dictionary to store values
        percentage_data = {
            "portfolio_percentage": None,
            "ndaq_percentage": None,
            "spy_percentage": None,
        }

        # Extract percentage values
        for entry in portfolio:
            if "portfolio_percentage" in entry:
                percentage_data["portfolio_percentage"] = entry["portfolio_percentage"]
            elif "ndaq_percentage" in entry:
                percentage_data["ndaq_percentage"] = entry["ndaq_percentage"]
            elif "spy_percentage" in entry:
                percentage_data["spy_percentage"] = entry["spy_percentage"]

        # Check if all values are found
        if (
            percentage_data["portfolio_percentage"] is None
            or percentage_data["ndaq_percentage"] is None
            or percentage_data["spy_percentage"] is None
        ):
            raise HTTPException(status_code=404, detail="One or more percentages not found")

        return percentage_data

    except Exception as e:
        print(f"Error fetching portfolio percentage: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch portfolio percentages")

# Pydantic model for Ticker output (Result of algorithm)
class TickerResult(BaseModel):
    ticker: str
    current_price: float
    decision: str
    median_quantity: int
    buy_weight: float
    sell_weight: float
    hold_weight: float

    class Config:
        json_encoders = {ObjectId: str}

@app.post("/ticker", response_model=TickerResult)
async def run_algorithm_on_ticker(ticker: str):
    decisions_and_quantities = []
    strategy_to_coefficient = {}
    
    try:
        for strategy in strategies:
            rank_doc = await rankings_collection.find({'strategy': strategy.__name__}).to_list(length = 1)
            
            if rank_doc is None:
                raise HTTPException(status_code=404, detail=f"Rank for strategy {strategy.__name__} not found")

            rank = rank_doc[0].get('rank', 0)

            coefficient_doc = await rank_to_coefficent_collection.find({'rank': rank}).to_list(length = 1)
            if coefficient_doc is None:
                raise HTTPException(status_code=404, detail=f"Coefficient for rank {rank} not found")
            
            coefficient = coefficient_doc[0].get('coefficient', 0)
            strategy_to_coefficient[strategy.__name__] = coefficient
        
        
        current_price = get_latest_price(ticker)
        historical_data = get_historical_data(ticker, data_client)
        buying_power = 50000.00
        portfolio_qty = 5
        portfolio_value = 75000.00
        
        for strategy in strategies:
            try:
                decision, quantity, _ = strategy(
                    ticker, current_price, historical_data, buying_power, portfolio_qty, portfolio_value
                )
                weight = strategy_to_coefficient[strategy.__name__]
            except Exception as e:
                print(f"Error running strategy {strategy.__name__}: {e}")
                continue
            decisions_and_quantities.append((decision, quantity, weight))
        
        decision, median_qty, buy_weight, sell_weight, hold_weight = weighted_majority_decision_and_median_quantity(
            decisions_and_quantities
        )
        
        # Construct result
        result = {
            "ticker": ticker,
            "current_price": current_price,
            "decision": decision,
            "median_quantity": median_qty,
            "buy_weight": buy_weight,
            "sell_weight": sell_weight,
            "hold_weight": hold_weight,
        }

        return result
    except Exception as e:
        print(f"Error running algorithm on ticker: {e}")
        raise HTTPException(status_code=500, detail="Failed to run algorithm on ticker")


@app.get("/ticker/{ticker}", response_model=Optional[TickerResult])
async def get_ticker_result(ticker: str):
    """
    Retrieves the result of the algorithm for a specific ticker.
    """
    
    decisions_and_quantities = []
    strategy_to_coefficient = {}
    
    try:
        for strategy in strategies:
            rank_doc = await rankings_collection.find({'strategy': strategy.__name__}).to_list(length = 1)
            
            if rank_doc is None:
                raise HTTPException(status_code=404, detail=f"Rank for strategy {strategy.__name__} not found")

            rank = rank_doc[0].get('rank', 0)

            coefficient_doc = await rank_to_coefficent_collection.find({'rank': rank}).to_list(length = 1)
            if coefficient_doc is None:
                raise HTTPException(status_code=404, detail=f"Coefficient for rank {rank} not found")
            
            coefficient = coefficient_doc[0].get('coefficient', 0)
            strategy_to_coefficient[strategy.__name__] = coefficient
        
        try:
            current_price = get_latest_price(ticker)
        except Exception as e:
            print(f"Error fetching latest price for {ticker}: {e}")
            return {
                "ticker": ticker,
                "current_price": 0,
                "decision": "ERROR",
                "median_quantity": 0,
                "buy_weight": 0,
                "sell_weight": 0,
                "hold_weight": 0,
            }

        
        historical_data = get_historical_data(ticker, data_client)
        buying_power = 50000.00
        portfolio_qty = 5
        portfolio_value = 75000.00
        
        for strategy in strategies:
            try:
                decision, quantity, _ = strategy(
                    ticker, current_price, historical_data, buying_power, portfolio_qty, portfolio_value
                )
                weight = strategy_to_coefficient[strategy.__name__]
            except Exception as e:
                print(f"Error running strategy {strategy.__name__}: {e}")
                continue
            decisions_and_quantities.append((decision, quantity, weight))
        
        decision, median_qty, buy_weight, sell_weight, hold_weight = weighted_majority_decision_and_median_quantity(
            decisions_and_quantities
        )
        
        # Construct result
        result = {
            "ticker": ticker,
            "current_price": current_price,
            "decision": decision,
            "median_quantity": median_qty,
            "buy_weight": buy_weight,
            "sell_weight": sell_weight,
            "hold_weight": hold_weight,
        }

        return result
    except Exception as e:
        print(f"Error running algorithm on ticker: {e}")
        raise HTTPException(status_code=500, detail="Failed to run algorithm on ticker")
def weighted_majority_decision_and_median_quantity(decisions_and_quantities):
    """
    Calculate the weighted majority decision and median quantity.
    """
    buy_decisions = ['buy', 'strong buy']
    sell_decisions = ['sell', 'strong sell']

    weighted_buy_quantities = []
    weighted_sell_quantities = []
    buy_weight = 0
    sell_weight = 0
    hold_weight = 0

    for decision, quantity, weight in decisions_and_quantities:
        if decision in buy_decisions:
            weighted_buy_quantities.extend([quantity])
            buy_weight += weight
        elif decision in sell_decisions:
            weighted_sell_quantities.extend([quantity])
            sell_weight += weight
        elif decision == 'hold':
            hold_weight += weight

    if buy_weight > sell_weight and buy_weight > hold_weight:
        return 'buy', median(weighted_buy_quantities)//1 if weighted_buy_quantities else 0, buy_weight, sell_weight, hold_weight
    elif sell_weight > buy_weight and sell_weight > hold_weight:
        return 'sell', median(weighted_sell_quantities)//1 if weighted_sell_quantities else 0, buy_weight, sell_weight, hold_weight
    else:
        return 'hold', 0, buy_weight, sell_weight, hold_weight
    
@app.get("/")
async def root():
    return {"message": "AmpyFin API is running!"}
