#!/bin/bash

API="http://localhost:8000"
echo "🔍 Testing Kong API Platform"
echo "================================="

echo ""
echo "1️⃣  Testing /health (public)..."
curl -s $API/health | jq .

echo ""
echo "2️⃣  Testing /login..."
TOKEN=$(curl -s -X POST $API/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}' | jq -r .access_token)
echo "✅ Token: ${TOKEN:0:40}..."

echo ""
echo "3️⃣  Testing /verify with token..."
curl -s -H "Authorization: Bearer $TOKEN" $API/verify | jq .

echo ""
echo "4️⃣  Testing /users (protected)..."
curl -s -H "Authorization: Bearer $TOKEN" $API/users | jq .

echo ""
echo "5️⃣  Testing /users without token (should fail)..."
curl -s $API/users | jq .

echo ""
echo "6️⃣  Testing rate limiting (send 12 requests)..."
for i in {1..12}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" $API/health)
  echo "Request $i: $STATUS"
done

echo ""
echo "✅ All tests complete!"
