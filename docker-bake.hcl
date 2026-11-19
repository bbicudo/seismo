# Build multiplataforma (arm64 + amd64) das imagens próprias, para publicar num registry.
#   docker buildx bake --push                       (CI ou máquina com buildx)
#   REGISTRY=ghcr.io/usuario TAG=0.1.0 docker buildx bake --push
# No lab usamos "docker compose build", que gera só a arquitetura nativa (arm64).

variable "REGISTRY" { default = "ghcr.io/CHANGE-ME" }
variable "TAG"      { default = "dev" }

group "default" { targets = ["collector", "api", "web"] }

target "_multi" {
  platforms = ["linux/arm64", "linux/amd64"]
  labels = { "org.opencontainers.image.source" = "https://github.com/CHANGE-ME/seismo" }
}

target "collector" {
  inherits = ["_multi"]
  context  = "./collector"
  tags     = ["${REGISTRY}/seismo-collector:${TAG}"]
}

target "api" {
  inherits = ["_multi"]
  context  = "./api"
  tags     = ["${REGISTRY}/seismo-api:${TAG}"]
}

target "web" {
  inherits = ["_multi"]
  context  = "./web"
  tags     = ["${REGISTRY}/seismo-web:${TAG}"]
}
