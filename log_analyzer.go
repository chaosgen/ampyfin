package main

import (
	"bufio"
	"fmt"
	"log"
	"net/http"
	"os"
	"strings"
)

// Function to analyze logs and return matching lines
func analyzeLogs(query string) ([]string, error) {
	file, err := os.Open("system.log")
	if err != nil {
		return nil, err
	}
	defer file.Close()

	var matchingLines []string
	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := scanner.Text()
		if strings.Contains(line, query) {
			matchingLines = append(matchingLines, line) // Collect matching lines
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, err
	}
	return matchingLines, nil
}

func main() {
	// HTTP handler for log analysis
	http.HandleFunc("/logs", func(w http.ResponseWriter, r *http.Request) {
		query := r.URL.Query().Get("q")
		if query == "" {
			http.Error(w, "Query parameter 'q' is required", http.StatusBadRequest)
			return
		}

		// Analyze logs based on query
		matchingLines, err := analyzeLogs(query)
		if err != nil {
			http.Error(w, fmt.Sprintf("Error analyzing logs: %v", err), http.StatusInternalServerError)
			return
		}

		// If no lines match, return a helpful message
		if len(matchingLines) == 0 {
			fmt.Fprintln(w, "No matching log entries found.")
			return
		}

		// Write matching lines to the HTTP response
		for _, line := range matchingLines {
			fmt.Fprintln(w, line)
		}
	})

	log.Println("Starting Log Analyzer server on :8083")
	log.Fatal(http.ListenAndServe(":8083", nil))
}

