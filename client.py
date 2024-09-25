from polygon import RESTClient
from config import POLYGON_API_KEY, FINANCIAL_PREP_API_KEY, MONGO_DB_USER, MONGO_DB_PASS
import json
import certifi
from urllib.request import urlopen
from pymongo import MongoClient
import logging
import time

# Set up logging configuration
logging.basicConfig(
    filename='system.log',  # Path to the log file
    level=logging.INFO,      # Set log level to INFO
    format='%(asctime)s - %(levelname)s - %(message)s',  # Log message format
    datefmt='%Y-%m-%d %H:%M:%S'  # Timestamp format
)

# Function to retrieve and store the list of NASDAQ 100 tickers in MongoDB
def call_ndaq_100():
    """
    Fetches the list of NASDAQ 100 tickers using an external API and stores it in a MongoDB collection.

    The MongoDB collection is cleared and then populated with the updated list of tickers.
    """
    logging.info("Calling NASDAQ 100 to retrieve tickers.")
    
    def get_jsonparsed_data(url):
        """
        Parses the JSON response from the provided URL.
        
        :param url: The API endpoint to retrieve data from.
        :return: Parsed JSON data as a dictionary.
        """
        response = urlopen(url, cafile=certifi.where())  # Secure URL request
        data = response.read().decode("utf-8")
        return json.loads(data)

    try:
        # API URL for fetching NASDAQ 100 tickers
        ndaq_url = f"https://financialmodelingprep.com/api/v3/nasdaq_constituent?apikey={FINANCIAL_PREP_API_KEY}"
        ndaq_stocks = get_jsonparsed_data(ndaq_url)  # Retrieve NASDAQ tickers
        logging.info("Successfully retrieved NASDAQ 100 tickers.")
    except Exception as e:
        logging.error(f"Error fetching NASDAQ 100 tickers: {e}")
        return
    
    try:
        # MongoDB connection details
        mongo_url = f"mongodb+srv://{MONGO_DB_USER}:{MONGO_DB_PASS}@cluster0.0qoxq.mongodb.net?retryWrites=true&writeConcern=majority"
        mongo_client = MongoClient(mongo_url)
        db = mongo_client.stock_list  # Select database
        ndaq100_tickers = db.ndaq100_tickers  # Select collection
        
        ndaq100_tickers.delete_many({})  # Clear existing data
        ndaq100_tickers.insert_many(ndaq_stocks)  # Insert new data
        logging.info("Successfully inserted NASDAQ 100 tickers into MongoDB.")
    except Exception as e:
        logging.error(f"Error inserting tickers into MongoDB: {e}")
    finally:
        mongo_client.close()  # Ensure MongoDB connection is closed
        logging.info("MongoDB connection closed.")

# Function to check the current market status (open, closed, early hours)
def market_status(client):
    """
    Checks the current market status by querying the Polygon API.

    :param client: An instance of the Polygon RESTClient.
    :return: A string indicating whether the market is 'open', in 'early_hours', or 'closed'.
    """
    logging.info("Checking market status.")
    
    try:
        status = client.get_market_status()  # Get market status
        
        # Check if both NASDAQ and NYSE are open
        if status.exchanges.nasdaq == "open" and status.exchanges.nyse == "open":
            logging.info("Market is open.")
            return "open"
        elif status.early_hours:
            logging.info("Market is in early hours.")
            return "early_hours"
        else:
            logging.info("Market is closed.")
            return "closed"
    except Exception as e:
        logging.error(f"Error retrieving market status: {e}")
        return "error"

# Main function that runs continuously, checking market status and executing trades or calculations
def main():
    """
    Main function to control the workflow based on the market's status.
    
    Continuously checks the market status and acts accordingly:
      - If 'open': Execute trading strategies based on market conditions.
      - If 'early_hours': Retrieve NASDAQ 100 tickers and perform premarket calculations.
      - If 'closed': Perform post-market analysis and possibly run AI-based calculations.
    """
    while True:
        client = RESTClient(api_key=POLYGON_API_KEY)  # Initialize Polygon API client
        status = market_status(client)  # Check the market status
        
        if status == "open":
            logging.info("Market is open. Waiting for 60 seconds.")
            # Add logic to execute trades based on current market conditions
            time.sleep(60)  # Wait for 60 seconds before the next iteration
        elif status == "early_hours":
            logging.info("Early hours detected. Calling NASDAQ 100 and waiting for 60 seconds.")
            call_ndaq_100()  # Fetch NASDAQ 100 tickers and prepare for market open
            time.sleep(60)  # Wait for 60 seconds
        else:
            logging.info("Market is closed or in error state. Waiting for 60 seconds.")
            # Post-market analysis or AI-driven momentum trading window calculation could go here
            time.sleep(60)  # Wait for 60 seconds before the next check

if __name__ == "__main__":
    main()  # Entry point for the script
