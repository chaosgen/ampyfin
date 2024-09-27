package main

import (
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"
)

// Mock API responses
var stockPrices = map[string]float64{
	"AAPL": 155.0,
	"TSLA": 240.0,
}

var mu sync.Mutex

func fetchStockData(symbol string) (float64, error) {
	// Mock API call, replace with real API call in production
	price, ok := stockPrices[symbol]
	if !ok {
		return 0.0, fmt.Errorf("stock price not available for: %s", symbol)
	}
	return price, nil
}

func updateMarketData(symbol string) {
	price, err := fetchStockData(symbol)
	if err != nil {
		log.Printf("Error fetching market data for %s: %v", symbol, err)
		return
	}

	mu.Lock()
	stockPrices[symbol] = price
	mu.Unlock()

	log.Printf("Updated %s price: %.2f", symbol, price)
}

func aggregateMarketData() {
	symbols := []string{"AAPL", "TSLA"}
	for _, symbol := range symbols {
		go updateMarketData(symbol)
	}
}

func main() {
	// Schedule data aggregation every 30 seconds
	ticker := time.NewTicker(30 * time.Second)
	go func() {
		for range ticker.C {
			aggregateMarketData()
		}
	}()

	// Simple HTTP server to keep the process running
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "Market Data Aggregator is running")
	})
	log.Println("Starting server on :8082")
	log.Fatal(http.ListenAndServe(":8082", nil))
}
