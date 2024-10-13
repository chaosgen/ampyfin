package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"regexp"
	"strconv"
	"strings"
)

// LogEntry represents a log entry structure
type LogEntry struct {
	Line      string `json:"line"`
	Timestamp string `json:"timestamp"` // Assuming logs have a timestamp
	Level     string `json:"level"`     // Assuming logs have a level (INFO, WARN, ERROR)
}

// Function to analyze logs
func analyzeLogs(queries []string, logLevel string, limit int, offset int) ([]LogEntry, error) {
	file, err := os.Open("system.log")
	if err != nil {
		return nil, fmt.Errorf("error opening log file: %w", err)
	}
	defer file.Close()

	var results []LogEntry
	scanner := bufio.NewScanner(file)

	for scanner.Scan() {
		line := scanner.Text()

		// Check if the line contains a log level if specified
		if logLevel != "" && !strings.Contains(line, logLevel) {
			continue
		}

		for _, query := range queries {
			// Use regex for more flexible matching
			matched, _ := regexp.MatchString(query, line)
			if matched {
				// Extract log level and timestamp if needed
				level := extractLogLevel(line) // Function to extract log level
				timestamp := extractTimestamp(line) // Function to extract timestamp

				results = append(results, LogEntry{Line: line, Level: level, Timestamp: timestamp})
				break
			}
		}
	}

	if err := scanner.Err(); err != nil {
		return nil, fmt.Errorf("error reading log file: %w", err)
	}

	// Implement pagination
	if offset > len(results) {
		return []LogEntry{}, nil
	}
	end := offset + limit
	if end > len(results) {
		end = len(results)
	}
	return results[offset:end], nil
}

// Dummy function to extract log level from a line (modify as per your log format)
func extractLogLevel(line string) string {
	// Example log format: "2024-01-01 12:00:00 INFO: Log message"
	parts := strings.Split(line, " ")
	if len(parts) > 2 {
		return parts[2]
	}
	return ""
}

// Dummy function to extract timestamp from a line (modify as per your log format)
func extractTimestamp(line string) string {
	// Example log format: "2024-01-01 12:00:00 INFO: Log message"
	parts := strings.Split(line, " ")
	if len(parts) > 1 {
		return parts[0] + " " + parts[1]
	}
	return ""
}

func main() {
	http.HandleFunc("/logs", func(w http.ResponseWriter, r *http.Request) {
		queries := r.URL.Query()["q"]
		logLevel := r.URL.Query().Get("level")
		limitStr := r.URL.Query().Get("limit")
		offsetStr := r.URL.Query().Get("offset")

		if len(queries) == 0 {
			http.Error(w, "Query parameter 'q' is required", http.StatusBadRequest)
			return
		}

		// Convert limit and offset from string to int
		limit := 10 // Default limit
		offset := 0 // Default offset

		if limitStr != "" {
			var err error
			limit, err = strconv.Atoi(limitStr)
			if err != nil || limit < 0 {
				http.Error(w, "Invalid limit parameter", http.StatusBadRequest)
				return
			}
		}
		if offsetStr != "" {
			var err error
			offset, err = strconv.Atoi(offsetStr)
			if err != nil || offset < 0 {
				http.Error(w, "Invalid offset parameter", http.StatusBadRequest)
				return
			}
		}

		// Analyze logs with the provided queries
		results, err := analyzeLogs(queries, logLevel, limit, offset)
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
