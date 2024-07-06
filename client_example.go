package main

import (
	"bytes"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/joho/godotenv"
)

func loadEnv() {
	err := godotenv.Load()
	if err != nil {
		log.Fatalf("Error loading .env file")
	}
}

func sendRequest(text string) {
	picoHIDServerURL := os.Getenv("PICO_HID_SERVER_URL")
	fmt.Println("Sending request: `" + text + "`")

	resp, err := http.Post(picoHIDServerURL, "text/plain", bytes.NewBufferString(text))
	if err != nil {
		log.Fatalf("Request failed: %v", err)
	}
	defer resp.Body.Close()

	body, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Fatalf("Error reading response: %v", err)
	}

	fmt.Printf("Response: %s (%d)\n", body, resp.StatusCode)
	if resp.StatusCode != http.StatusOK {
		log.Fatalf("Request failed with status code: %d", resp.StatusCode)
	}
}

func keycodeInput(key string) {
	sendRequest("keycode=" + key)
	time.Sleep(3 * time.Second)
}

func mouseClick(x, y int) {
	sendRequest(fmt.Sprintf("mouse=CLICK(%d,%d)", x, y))
}

func mouseDoubleClick(x, y int) {
	sendRequest(fmt.Sprintf("mouse=DOUBLE_CLICK(%d,%d)", x, y))
}

func mouseRightClick(x, y int) {
	sendRequest(fmt.Sprintf("mouse=RIGHT_CLICK(%d,%d)", x, y))
}

func mouseMove(x, y int) {
	sendRequest(fmt.Sprintf("mouse=MOVE(%d,%d)", x, y))
}

func typing(text string) {
	sendRequest("typing=" + text)
}

func main() {
	loadEnv()
	fmt.Println("Server URL: " + os.Getenv("PICO_HID_SERVER_URL"))

	// Your code here
}
