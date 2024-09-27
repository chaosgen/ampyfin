package main

import (
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/go-co-op/gocron"
)

type Alert struct {
	Symbol    string
	Threshold float64
	Above     bool // True for alerting if price goes above the threshold, false if below
}

var alerts = []Alert{
	{"AAPL", 150.0, true},
	{"TSLA", 250.0, false},
}

func getStockPrice(symbol string) (float64, error) {
	// Mock fetching stock price
	// In real implementation, this would fetch from an API like Alpaca, Yahoo Finance, etc.
	prices := map[string]float64{
		"AAPL": 155.0,
		"TSLA": 240.0,
	}
	if price, ok := prices[symbol]; ok {
		return price, nil
	}
	return 0.0, fmt.Errorf("price not found for symbol: %s", symbol)
}

func checkAlerts() {
	for _, alert := range alerts {
		price, err := getStockPrice(alert.Symbol)
		if err != nil {
			log.Println("Error fetching price:", err)
			continue
		}
		if (alert.Above && price > alert.Threshold) || (!alert.Above && price < alert.Threshold) {
			log.Printf("Price alert triggered for %s! Current Price: %.2f, Threshold: %.2f\n", alert.Symbol, price, alert.Threshold)
		}
	}
}

func main() {
	// Schedule the alert checker every minute
	s := gocron.NewScheduler(time.UTC)
	s.Every(1).Minute().Do(checkAlerts)
	s.StartAsync()

	// Simple HTTP server to keep the process running
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "Price Alert System is running")
	})
	log.Println("Starting server on :8080")
	log.Fatal(http.ListenAndServe(":8080", nil))
}
