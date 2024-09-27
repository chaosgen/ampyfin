package main

import (
	"fmt"
	"log"
	"net/http"
	"time"
)

type Portfolio struct {
	InitialValue float64
	CurrentValue float64
	Symbols      []string
}

var portfolio = Portfolio{
	InitialValue: 100000.0,
	CurrentValue: 95000.0,
	Symbols:      []string{"AAPL", "TSLA"},
}

const riskThreshold = 0.10 // 10% drop alert

func checkRisk() {
	drop := (portfolio.InitialValue - portfolio.CurrentValue) / portfolio.InitialValue
	if drop >= riskThreshold {
		log.Printf("Risk alert! Portfolio has dropped by %.2f%%. Current Value: %.2f\n", drop*100, portfolio.CurrentValue)
	}
}

func main() {
	// Schedule risk management checks every hour
	ticker := time.NewTicker(1 * time.Hour)
	go func() {
		for range ticker.C {
			checkRisk()
		}
	}()

	// Simple HTTP server to keep the process running
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		fmt.Fprintln(w, "Risk Management System is running")
	})
	log.Println("Starting server on :8081")
	log.Fatal(http.ListenAndServe(":8081", nil))
}
