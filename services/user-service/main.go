package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"time"

	"github.com/segmentio/kafka-go"
)

type User struct {
	Email string `json:"email"`
	Name  string `json:"name"`
}

var writer *kafka.Writer

func main() {
	// Kafka writer'ı ayağa kaldıralım
	writer = kafka.NewWriter(kafka.WriterConfig{
		Brokers:  []string{"redpanda:9092"}, // container içinden redpanda
		Topic:    "user.events",             // Redpanda'da oluşturduğun topic
		Balancer: &kafka.LeastBytes{},
	})
	defer writer.Close()

	http.HandleFunc("/health", healthHandler)
	http.HandleFunc("/users/create", createUserHandler)

	log.Println("user-service running on :8081")
	if err := http.ListenAndServe(":8081", nil); err != nil {
		log.Fatal(err)
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	resp := map[string]string{
		"status":  "OK",
		"service": "user-service",
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(resp)
}

func createUserHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "only POST allowed", http.StatusMethodNotAllowed)
		return
	}

	var u User
	if err := json.NewDecoder(r.Body).Decode(&u); err != nil {
		log.Println("failed to decode user:", err)
		http.Error(w, "invalid body", http.StatusBadRequest)
		return
	}

	payload, err := json.Marshal(u)
	if err != nil {
		log.Println("failed to marshal user:", err)
		http.Error(w, "internal error", http.StatusInternalServerError)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	msg := kafka.Message{
		Key:   []byte(u.Email),
		Value: payload,
	}

	if err := writer.WriteMessages(ctx, msg); err != nil {
		log.Println("Failed to publish event:", err)
		http.Error(w, "Kafka publish error", http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	resp := map[string]string{
		"status": "ok",
		"email":  u.Email,
		"name":   u.Name,
	}
	json.NewEncoder(w).Encode(resp)
}
