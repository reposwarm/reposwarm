#!/usr/bin/env bash
set -euo pipefail

AWS_PROFILE_DEFAULT="niro-dev"
AWS_REGION_DEFAULT="ap-southeast-2"
ECR_REGISTRY_DEFAULT="219277046067.dkr.ecr.ap-southeast-2.amazonaws.com"
IMAGE_NAME_DEFAULT="chen-test-cve"
IMAGE_TAG_DEFAULT="reposwarm-latest"
KUBECONFIG_DEFAULT="$HOME/.kube/config-dev.yaml"
K8S_MANIFEST_DEFAULT="k8s/reposwarm.yaml"

AWS_PROFILE_VALUE="${AWS_PROFILE:-$AWS_PROFILE_DEFAULT}"
AWS_REGION_VALUE="${AWS_REGION:-$AWS_REGION_DEFAULT}"
ECR_REGISTRY_VALUE="${ECR_REGISTRY:-$ECR_REGISTRY_DEFAULT}"
IMAGE_NAME_VALUE="${IMAGE_NAME:-$IMAGE_NAME_DEFAULT}"
IMAGE_TAG_VALUE="${IMAGE_TAG:-$IMAGE_TAG_DEFAULT}"
KUBECONFIG_VALUE="${KUBECONFIG:-$KUBECONFIG_DEFAULT}"
K8S_MANIFEST_VALUE="${K8S_MANIFEST:-$K8S_MANIFEST_DEFAULT}"
IMAGE_URI="${ECR_REGISTRY_VALUE}/${IMAGE_NAME_VALUE}:${IMAGE_TAG_VALUE}"

usage() {
  cat <<'EOF'
Usage: scripts/deploy.sh [build|deploy|all]

Commands:
  build   Login to ECR and build/push multi-arch image
  deploy  Apply Kubernetes manifest
  all     Run build then deploy (default)

Environment variable overrides:
  AWS_PROFILE   (default: niro-dev)
  AWS_REGION    (default: ap-southeast-2)
  ECR_REGISTRY  (default: 219277046067.dkr.ecr.ap-southeast-2.amazonaws.com)
  IMAGE_NAME    (default: chen-test-cve)
  IMAGE_TAG     (default: reposwarm-latest)
  KUBECONFIG    (default: $HOME/.kube/config-dev.yaml)
  K8S_MANIFEST  (default: k8s/reposwarm.yaml)
EOF
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

build_image() {
  require_cmd aws
  require_cmd docker

  export AWS_PROFILE="$AWS_PROFILE_VALUE"
  echo "Using AWS_PROFILE=${AWS_PROFILE}"
  echo "Logging in to ECR registry ${ECR_REGISTRY_VALUE}"
  aws ecr get-login-password --region "$AWS_REGION_VALUE" \
    | docker login --username AWS --password-stdin "$ECR_REGISTRY_VALUE"

  echo "Building and pushing image ${IMAGE_URI}"

  docker buildx build --platform linux/amd64,linux/arm64 -t "$IMAGE_URI" .

  docker push "$IMAGE_URI"
}

deploy_k8s() {
  require_cmd kubectl

  export KUBECONFIG="$KUBECONFIG_VALUE"
  echo "Using KUBECONFIG=${KUBECONFIG}"
  echo "Applying Kubernetes manifest ${K8S_MANIFEST_VALUE}"
  kubectl apply -f "$K8S_MANIFEST_VALUE"
}

main() {
  local cmd="${1:-all}"

  case "$cmd" in
    build)
      build_image
      ;;
    deploy)
      deploy_k8s
      ;;
    all)
      build_image
      deploy_k8s
      ;;
    -h|--help|help)
      usage
      ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
