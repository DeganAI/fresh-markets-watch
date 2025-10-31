#!/bin/bash
# Fresh Markets Watch - API Test Script

set -e

BASE_URL="${1:-http://localhost:8000}"

echo "Testing Fresh Markets Watch API"
echo "Base URL: $BASE_URL"
echo ""

# Test health endpoint
echo "1. Testing /health endpoint..."
curl -s "$BASE_URL/health" | python3 -m json.tool
echo ""

# Test info endpoint
echo "2. Testing /info endpoint..."
curl -s "$BASE_URL/info" | python3 -m json.tool
echo ""

# Test landing page
echo "3. Testing landing page (/)..."
curl -s -o /dev/null -w "HTTP Status: %{http_code}\n" "$BASE_URL/"
echo ""

# Test scan endpoint (will fail without payment in non-free mode)
echo "4. Testing /scan endpoint (without payment)..."
curl -s -X POST "$BASE_URL/scan" \
  -H "Content-Type: application/json" \
  -d '{"chain": "ethereum", "window_minutes": 5}' | python3 -m json.tool
echo ""

echo "API tests completed!"
echo ""
echo "Note: /scan endpoint may require payment (x402) depending on FREE_MODE setting"
echo "To test with payment, add: -H 'X-Payment-TxHash: 0x...'"
