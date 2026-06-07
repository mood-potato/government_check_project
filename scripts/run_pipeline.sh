#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_NAME="${PROJECT_NAME:-government_project}"
DOCKER_COMPOSE="${DOCKER_COMPOSE:-docker compose}"
ENV_FILE="${ENV_FILE:-.env}"
PIPELINE_STAGES_ARG="${PIPELINE_STAGES:-}"
RESET=0
BUILD=0
USE_SUPABASE=0

usage() {
  cat <<'EOF'
Usage: scripts/run_pipeline.sh [options]

Options:
  --reset              Stop the Compose stack and delete volumes before running.
  --build              Build images before running the pipeline.
  --stages STAGES      Comma-separated pipeline stages to run.
  --env-file FILE      Env file to use. Default: .env
  --use-supabase       Do not clear SUPABASE_DATABASE_URL for the pipeline container.
  -h, --help           Show this help.

Examples:
  scripts/run_pipeline.sh --build
  scripts/run_pipeline.sh --reset --build
  scripts/run_pipeline.sh --stages bill-speech
  scripts/run_pipeline.sh --stages speaker-seed,bill-url-workbook,bill-speech,vectorize,contradiction,home
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --reset)
      RESET=1
      shift
      ;;
    --build)
      BUILD=1
      shift
      ;;
    --stages)
      PIPELINE_STAGES_ARG="${2:?--stages requires a value}"
      shift 2
      ;;
    --env-file)
      ENV_FILE="${2:?--env-file requires a value}"
      shift 2
      ;;
    --use-supabase)
      USE_SUPABASE=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$ROOT_DIR"
read -r -a COMPOSE_CMD <<< "$DOCKER_COMPOSE"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ "$ENV_FILE" == ".env" && -f ".env.example" ]]; then
    cp .env.example .env
    echo "Created .env from .env.example. Check OPEN_GOVERMENT_API_KEY if you run API stages."
  else
    echo "Env file not found: $ENV_FILE" >&2
    exit 1
  fi
fi

if [[ "$RESET" -eq 1 ]]; then
  echo "Resetting Compose stack and deleting volumes for project '$PROJECT_NAME'."
  "${COMPOSE_CMD[@]}" -p "$PROJECT_NAME" --env-file "$ENV_FILE" down -v --remove-orphans
fi

UP_ARGS=(-p "$PROJECT_NAME" --env-file "$ENV_FILE" up -d)
RUN_ARGS=(-p "$PROJECT_NAME" --env-file "$ENV_FILE" --profile pipeline run --rm)

if [[ "$BUILD" -eq 1 ]]; then
  UP_ARGS+=(--build)
  RUN_ARGS+=(--build)
fi

echo "Starting Postgres and Elasticsearch."
"${COMPOSE_CMD[@]}" "${UP_ARGS[@]}" postgres elasticsearch

echo "Running pipeline container."
if [[ -n "$PIPELINE_STAGES_ARG" ]]; then
  echo "PIPELINE_STAGES=$PIPELINE_STAGES_ARG"
  ENV_ARGS=(-e "PIPELINE_STAGES=$PIPELINE_STAGES_ARG")
else
  ENV_ARGS=()
fi

if [[ "$USE_SUPABASE" -eq 0 ]]; then
  ENV_ARGS+=(-e "SUPABASE_DATABASE_URL=")
fi

"${COMPOSE_CMD[@]}" "${RUN_ARGS[@]}" "${ENV_ARGS[@]}" pipeline
