// surf-proxy is a small HTTP server that forwards requests through
// github.com/enetx/surf so callers get a Chrome TLS / HTTP-2 fingerprint
// without having to take a Go dependency in their own code.
//
// Endpoints:
//
//	POST /proxy  - body: ProxyRequest JSON, returns ProxyResponse JSON
//	GET  /health - liveness check, returns {"status":"ok","backend":"surf"}
//
// Configuration (env vars):
//
//	SURF_PROXY_PORT  - listen port (default 9876)
//	SURF_PROXY_DEBUG - "1" to log every forwarded request
package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"

	"github.com/enetx/g"
	"github.com/enetx/surf"
)

// ProxyRequest is the JSON body sent from Python.
type ProxyRequest struct {
	Method  string            `json:"method"`
	URL     string            `json:"url"`
	Headers map[string]string `json:"headers"`
	Body    string            `json:"body"`
	Timeout int               `json:"timeout"`
}

// ProxyResponse is the JSON body returned to Python.
type ProxyResponse struct {
	StatusCode int               `json:"status_code"`
	Headers    map[string]string `json:"headers"`
	Body       string            `json:"body"`
	Proto      string            `json:"proto,omitempty"`
	Time       int64             `json:"time_ms,omitempty"`
	Error      string            `json:"error,omitempty"`
}

// newSurfClient returns a configured surf client with Chrome impersonation.
// We rebuild the client per request rather than reusing one because
// different callers may need different header overrides and the cost is low
// (a builder call, no network I/O).
func newSurfClient() *surf.Client {
	return surf.NewClient().
		Builder().
		Impersonate().
		Chrome().
		Session().
		CacheBody().
		Build().
		Unwrap()
}

// handleProxy forwards a single request through surf and returns the response.
func handleProxy(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "POST only", http.StatusMethodNotAllowed)
		return
	}

	raw, err := io.ReadAll(r.Body)
	if err != nil {
		writeJSONError(w, http.StatusBadRequest, fmt.Sprintf("read body: %v", err))
		return
	}
	defer r.Body.Close()

	var req ProxyRequest
	if err := json.Unmarshal(raw, &req); err != nil {
		writeJSONError(w, http.StatusBadRequest, fmt.Sprintf("parse json: %v", err))
		return
	}

	if req.URL == "" {
		writeJSONError(w, http.StatusBadRequest, "url is required")
		return
	}

	// Sanity-check URL: refuse anything that isn't http(s).
	parsed, err := url.Parse(req.URL)
	if err != nil {
		writeJSONError(w, http.StatusBadRequest, fmt.Sprintf("invalid url: %v", err))
		return
	}
	if parsed.Scheme != "http" && parsed.Scheme != "https" {
		writeJSONError(w, http.StatusBadRequest, "only http/https allowed")
		return
	}

	timeout := time.Duration(req.Timeout) * time.Second
	if timeout <= 0 {
		timeout = 30 * time.Second
	}

	method := strings.ToUpper(req.Method)
	if method == "" {
		method = http.MethodGet
	}

	client := newSurfClient()

	// Build the request through surf. Body is set as a string; surf handles
	// Content-Length and framing for us.
	var sreq *surf.Request
	target := g.String(parsed.String())
	switch method {
	case http.MethodGet:
		sreq = client.Get(target)
	case http.MethodPost:
		sreq = client.Post(target)
	case http.MethodPut:
		sreq = client.Put(target)
	case http.MethodDelete:
		sreq = client.Delete(target)
	case http.MethodPatch:
		sreq = client.Patch(target)
	case http.MethodHead:
		sreq = client.Head(target)
	default:
		writeJSONError(w, http.StatusBadRequest, "unsupported method: "+method)
		return
	}

	// Caller-supplied headers go in last so impersonation defaults win only
	// for fields the caller did not specify.
	if len(req.Headers) > 0 {
		headers := g.NewMapOrd[g.String, g.String]()
		for k, v := range req.Headers {
			headers.Insert(g.String(k), g.String(v))
		}
		sreq.SetHeaders(headers)
	}

	if req.Body != "" && (method == http.MethodPost || method == http.MethodPut || method == http.MethodPatch) {
		sreq.Body(strings.NewReader(req.Body))
	}

	if os.Getenv("SURF_PROXY_DEBUG") == "1" {
		log.Printf("→ %s %s (timeout=%s, headers=%d)", method, parsed.String(), timeout, len(req.Headers))
	}

	start := time.Now()
	resp := sreq.WithContext(r.Context()).Do()
	elapsed := time.Since(start)

	if resp.IsErr() {
		log.Printf("surf error on %s %s: %v", method, parsed.String(), resp.Err())
		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(ProxyResponse{
			Error:      resp.Err().Error(),
			StatusCode: 0,
			Time:       elapsed.Milliseconds(),
		})
		return
	}

	body, _ := resp.Ok().Body.String().Unwrap(), 0
	_ = body

	// Use UTF8 conversion to handle non-utf8 bytes gracefully; fall back to
	// raw string on conversion error.
	var bodyStr string
	if s := resp.Ok().Body.UTF8(); s.IsOk() {
		bodyStr = s.Ok().Std()
	} else if b := resp.Ok().Body.String(); b.IsOk() {
		bodyStr = b.Ok().Std()
	} else if by := resp.Ok().Body.Bytes(); by.IsOk() {
		bodyStr = string(by.Ok())
	}

	// Flatten response headers.
	headers := make(map[string]string)
	for k, v := range resp.Ok().Headers {
		if len(v) > 0 {
			headers[k] = v[0]
		}
	}

	if os.Getenv("SURF_PROXY_DEBUG") == "1" {
		log.Printf("← %s %s -> %d (%d bytes, %s, %dms)",
			method, parsed.String(),
			resp.Ok().StatusCode, len(bodyStr), resp.Ok().Proto, elapsed.Milliseconds())
	}

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(ProxyResponse{
		StatusCode: int(resp.Ok().StatusCode),
		Headers:    headers,
		Body:       bodyStr,
		Proto:      string(resp.Ok().Proto),
		Time:       elapsed.Milliseconds(),
	})
}

// writeJSONError is a small helper for surf-proxy-internal errors so callers
// always get a parseable JSON body.
func writeJSONError(w http.ResponseWriter, code int, msg string) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(ProxyResponse{Error: msg})
}

func handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(map[string]any{
		"status":  "ok",
		"backend": "surf",
		"version": "1.0.0",
		"time":    time.Now().UTC().Format(time.RFC3339),
	})
}

func main() {
	port := os.Getenv("SURF_PROXY_PORT")
	if port == "" {
		port = "9876"
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/proxy", handleProxy)
	mux.HandleFunc("/health", handleHealth)

	addr := "127.0.0.1:" + port
	log.Printf("surf-proxy listening on %s (Chrome TLS fingerprint, surf v1.0.187)", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
