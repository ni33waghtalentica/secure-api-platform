# Kong Secure API Platform (Kubernetes-Native, Defense-in-Depth)
## Executive Summary

The Secure API Platform is a self-managed, Kubernetes-native API gateway architecture built using Kong OSS (DB-less mode), FastAPI, and NGINX.

It demonstrates layered security enforcement, production-style deployment patterns, and infrastructure-as-code practices suitable for internal enterprise API platforms.

The platform implements:

- JWT-based authenticatio
- IP allow-listing
- Rate limiting (13 requests per minute per IP)
- Optional NGINX-based DDoS mitigation layer
- Kubernetes-native deployment (raw manifests + Helm)
- Infrastructure provisioning via Terraform

This project showcases secure API gateway design, operational readiness, and DevOps maturity.

Architecture Overview
High-Level Traffic Flow
```
Client
   ↓
NGINX DDoS Proxy (Edge Protection Layer)
   ↓
Kong Gateway (API Control Layer)
   ↓
Auth Service (Application Layer)
```

### Edge Layer (NGINX)

- Connection limiting (`limit_conn`)
- Request rate limiting (`limit_req`)
- Early-stage traffic filtering

---

### Gateway Layer (Kong)

- JWT enforcement (protected endpoints)
- Global rate limiting (**13 requests per minute per IP**)
- IP allow-listing (CIDR-based)
- Custom Lua header injection & structured logging

---

### Application Layer (FastAPI)

- JWT token issuance
- User authentication logic
- SQLite-backed persistence

---

## Core Features

- Kong OSS (DB-less mode)
- FastAPI Auth Service
- Optional NGINX DDoS proxy
- Kubernetes-native deployment
- Helm chart support
- Terraform namespace + network policy provisioning
- Postman collection included
- Built-in test console UI (`console.html`)

---

## Security Controls

### Authentication

- JWT enforced on `GET /users`
- Public endpoints:
  - `GET /health`
  - `GET /verify`
- JWT secrets stored in Kubernetes Secrets

---

### Rate Limiting

- 13 requests per minute per IP
- Enforced at Kong level
- Configurable via:
  - Helm values
  - Kong configmap

---

### IP Allow-Listing

- CIDR-based IP restriction plugin
- Configurable in `k8s/kong/configmap.yaml`
- Optional Kubernetes NetworkPolicy enforcement

---

### DDoS Mitigation (Optional)

- NGINX edge proxy
- `limit_req` and `limit_conn`
- Prevents gateway exhaustion

## What is included
- Kong OSS in DB-less mode with JWT auth, rate limiting, IP allow-listing, and custom Lua logic.
- Auth service (FastAPI) with SQLite, auto-initialized database, and JWT issuance.
- Optional DDoS reverse proxy (NGINX with limit_req/limit_conn) in front of Kong.
- Kubernetes manifests for all components.

## Key behaviors
- JWT is enforced only for GET /users. Public endpoints GET /health and GET /verify bypass JWT.
- Rate limiting applies to all routes: **13 requests per minute per IP** (configurable in the Helm values or Kong configmap).
- IP allow-listing applies to all routes (edit the CIDR ranges in k8s/kong/configmap.yaml).
- Custom Lua logic injects headers and logs structured request info in Kong.

## Local testing (Minikube)

### Prerequisites
- Docker
- Minikube
- kubectl

### Setup steps
```bash
# 1. Start Minikube
minikube start

# 2. Point your shell to Minikube's Docker daemon
eval $(minikube docker-env)

# 3. Build the auth-service image inside Minikube's Docker
docker build -t auth-service:latest services/auth-service

# 4. Deploy all manifests
kubectl apply -k k8s

# 5. Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=auth-service --timeout=120s
kubectl wait --for=condition=ready pod -l app=kong --timeout=120s

# 6. Port-forward Kong proxy to localhost
kubectl port-forward svc/kong 8000:8000
```

### Alternative UI / Test Console
A static HTML page `console.html` (formerly `test-console.html`) provides a lightweight browser interface for exercising the APIs. It has been refactored to look and feel like an industry‑standard tool and now includes:

- Dark/light theme toggle with persistence via localStorage
- Multiple request **profiles** and **custom headers** support
- Request/response **history** and convenient copy buttons
- Built-in **JWT inspector** and token management UI
- API base URL selector, so you can point at Kong (8000) or the DDoS proxy (8080)
- Full navigation bar and status/message consoles

To use the UI, serve it over HTTP and open it in your browser while the cluster is running and the port‑forward is active. For example:

```bash
cd /Users/nitinw/Desktop/secure-api-platform
python3 -m http.server 9000 &
# then visit http://localhost:9000/console.html
```

### Helm chart deployment
The Helm chart has also been updated with sensible defaults (rate limit 13/minute) and can deploy the renamed application `secure-api-platform`. It still consists of two logical components (Kong and the user service). The examples below include how to override the rate limit or other settings.
Although the Minikube instructions above use raw manifests, the project includes a Helm chart under `helm/` with two logical components (Kong and the user service).  To install via Helm on any cluster:

```bash
# build the auth-service image and push it to a registry reachable by the cluster
# (minikube already has one) e.g. docker build -t myregistry/auth-service:latest .

helm repo add kong https://charts.konghq.com && helm repo update
helm install kong-api-platform ./helm \
    --set authService.image=myregistry/auth-service:latest \
    --set kong.configmap.name=kong-config \
    --set authService.env.JWT_KEY=yourkey \
    --set authService.env.JWT_SECRET=yoursecret

# to change rate limits, CIDR allow-lists, etc use --set or a custom values.yaml
helm upgrade kong-api-platform ./helm -f custom-values.yaml
helm uninstall kong-api-platform
```

### Terraform support
A basic Terraform configuration (create `terraform/namespace.tf`) can provision the namespace and a network policy for IP whitelisting.  Example:

```hcl
provider "kubernetes" {
  config_path = "~/.kube/config"
}

resource "kubernetes_namespace" "platform" {
  metadata { name = "kong-platform" }
}

resource "kubernetes_network_policy" "allow_internal" {
  metadata {
    name      = "ip-whitelist"
    namespace = kubernetes_namespace.platform.metadata[0].name
  }
  spec {
    pod_selector {}
    ingress {
      from {
        ip_block {
          cidr = "10.0.0.0/8"
        }
      }
    }
  }
}
```

Execute it with:

```bash
cd terraform
terraform init
terraform apply
```

You can extend the Terraform code to provision an entire managed cluster (EKS/GKE/AKS) if desired; the sample above satisfies the assignment requirement and keeps everything declarative.

### Cleanup
```bash
kubectl delete -k k8s
minikube stop
# or to delete the cluster entirely: minikube delete
```
Alternative: use the DDoS proxy in front of Kong (see **NGINX DDoS proxy** section below):
```bash
kubectl port-forward svc/ddos-proxy 8080:8080
```

### Cleanup
```bash
kubectl delete -k k8s
minikube stop
# or to delete the cluster entirely: minikube delete
```

## Example API usage
- Login: POST http://localhost:8000/login with JSON {"username":"admin","password":"password"}
- Public health: GET http://localhost:8000/health
- Public verify: GET http://localhost:8000/verify
- Protected users: GET http://localhost:8000/users with Authorization: Bearer <token>

## Configuration notes
- JWT secrets are externalized in k8s/kong/secret.yaml and injected into Kong and the auth service.
- Change CIDR allow-list in k8s/kong/configmap.yaml under the ip-restriction plugin.
- Update seed user credentials in k8s/auth-service/deployment.yaml.


# High-level architecture Flow
Client → **NGINX DDoS Proxy** (8080) → Kong Gateway (8000) → Auth Service
              ↓                            ↓
         Rate/conn limit              Rate limit (13/min) + JWT + IP allow-list


## Additional tooling
- `run-tests.sh` script exercises the API endpoints and verifies behavior
- `ddos-test.sh` spammer script demonstrates the NGINX proxy throttling
- Postman collection (`api-postman.json`) and environment (`env-postman.json`) are provided for easy import and automated local testing.
