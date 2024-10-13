package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strings"
)

// LogEntry represents a log entry structure
type LogEntry struct {
	Line      string `json:"line"`
	Timestamp string `json:"timestamp"` // Assuming logs have a timestamp
}

// Function to analyze logs
func analyzeLogs(queries []string) ([]LogEntry, error) {
	file, err := os.Open("system.log")
	if err != nil {
		return nil, fmt.Errorf("error opening log file: %w", err)
	}
	defer file.Close()

	var results []LogEntry
	scanner := bufio.NewScanner(file)

	for scanner.Scan() {
		line := scanner.Text()
		for _, query := range queries {
			// Use regex for more flexible matching
			matched, _ := regexp.MatchString(query, line)
			if matched {
				results = append(results, LogEntry{Line: line}) // Add timestamp if available
				break
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading log file: %w", err)
	}
	return results, nil
}

func main() {
	http.HandleFunc("/logs", func(w http.ResponseWriter, r *http.Request) {
		queries := r.URL.Query()["q"]
		if len(queries) == 0 {
			http.Error(w, "Query parameter 'q' is required", http.StatusBadRequest)
			return
		}

		// Analyze logs with the provided queries
		results, err := analyzeLogs(queries)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}

		// Return results as JSON
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(results)
	})

	log.Println("Starting Log Analyzer server on :8083")
	log.Fatal(http.ListenAndServe(":8083", nil))
}