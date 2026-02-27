#!/bin/bash
# Test Kong API Platform via curl (Minikube/k8s direct)

set -e
KONG_URL="http://localhost:8000"

# 1. Health (no auth, no rate limit)
echo "\n[1] /health (should succeed, no auth)"
curl -i "$KONG_URL/health"

# 2. Verify (no auth, no rate limit)
echo "\n[2] /verify (should succeed, no auth)"
curl -i "$KONG_URL/verify"

# 3. Login as admin (get JWT)
echo "\n[3] /login (admin)"
ADMIN_JWT=$(curl -s -X POST "$KONG_URL/login" -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "Admin JWT: $ADMIN_JWT"

# 4. Create user (should succeed)
echo "\n[4] /users (POST, create user1)"
curl -i -X POST "$KONG_URL/users" -H "Authorization: Bearer $ADMIN_JWT" -H 'Content-Type: application/json' -d '{"username":"user1","password":"userpass"}'

# 5. Login as user1 (get JWT)
echo "\n[5] /login (user1)"
USER1_JWT=$(curl -s -X POST "$KONG_URL/login" -H 'Content-Type: application/json' -d '{"username":"user1","password":"userpass"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
echo "User1 JWT: $USER1_JWT"

# 6. List users (should succeed with admin JWT)
echo "\n[6] /users (GET, admin JWT)"
curl -i -H "Authorization: Bearer $ADMIN_JWT" "$KONG_URL/users"

# 7. List users (should fail with user1 JWT)
echo "\n[7] /users (GET, user1 JWT, should fail)"
curl -i -H "Authorization: Bearer $USER1_JWT" "$KONG_URL/users"

# 8. Rate limit test (should hit 429 after 10 requests/min)
echo "\n[8] Rate limit test (11 requests)"
for i in {1..11}; do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" "$KONG_URL/health"
done

# 9. IP allow-list test (should succeed from allowed IP)
echo "\n[9] IP allow-list test (should succeed from localhost)"
curl -i "$KONG_URL/health"

# 10. Custom header and logging (check X-Platform, X-Gateway headers)"
echo "\n[10] Custom header and logging (check headers)"
curl -i "$KONG_URL/health"
