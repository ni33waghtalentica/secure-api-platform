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
