# Kong API Platform Helm Chart

This Helm chart deploys the following components on Minikube:
- Kong API Gateway (DB-less, declarative config)
- FastAPI Auth Service (with SQLite and PVC)
- NGINX DDoS Proxy (rate limiting, connection limiting)

## Usage

1. Edit `values.yaml` to customize images, ports, and environment variables as needed.
2. Place your Kong declarative config in `kong-configmap.yaml` or mount via values.
3. Install the chart:

```sh
helm install kong-api-platform ./helm
```

4. To upgrade:
```sh
helm upgrade kong-api-platform ./helm
```

5. To uninstall:
```sh
helm uninstall kong-api-platform
```

## Notes
- PVC is used for SQLite persistence in the auth-service.
- NGINX forwards to Kong and applies DDoS protection.
- Kong runs in DB-less mode with declarative config.

## Structure
- `templates/` - All Kubernetes manifests
- `values.yaml` - Main configuration
- `Chart.yaml` - Chart metadata

