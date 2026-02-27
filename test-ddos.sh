#!/bin/bash
# Simulate DDoS by sending many requests in parallel to NGINX DDoS proxy (Minikube/k8s)

set -e
KONG_URL="http://localhost:8000"
CONCURRENT=20
TOTAL=50

# Start port-forward if not already running
# kubectl port-forward svc/ddos-proxy 8080:8080 &
# sleep 2

echo "[DDoS Test] Sending $TOTAL requests with $CONCURRENT concurrent clients to $KONG_URL/health"

run_attack() {
  for i in $(seq 1 $TOTAL); do
    (
      curl -s -o /dev/null -w "Request $i: %{http_code}\n" "$KONG_URL/health" &
      if (( $((i % CONCURRENT)) == 0 )); then wait; fi
    )
  done
  wait
}

run_attack | tee ddos-test.log

echo "\nCheck ddos-test.log for 429 (Too Many Requests) and 503 (connection limit) responses."
