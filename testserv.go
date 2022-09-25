package main

import (
    "fmt"
    "net/http"
    "math/rand"
    "strconv"
)

func number(w http.ResponseWriter, req *http.Request) {

    fmt.Fprintf(w, strconv.Itoa(rand.Intn(100)))
}


func main() {

    http.HandleFunc("/", number)

    http.ListenAndServe(":8090", nil)
}
