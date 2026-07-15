#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NO_ALBUMENTATIONS_UPDATE="${NO_ALBUMENTATIONS_UPDATE:-1}"
VENV_DIR="${ATTNDIST_VENV_DIR:-$ROOT/.venv}"
export MPLCONFIGDIR="${MPLCONFIGDIR:-$VENV_DIR/.matplotlib}"
STAMP_FILE="$VENV_DIR/.attndist-install-stamp"
UI_DIR="$ROOT/web"
UI_STAMP_FILE="$UI_DIR/.attndist-install-stamp"
TRAIN_PID_FILE="$ROOT/outputs_v2/training.pid"
TRAIN_LOG_FILE="${ATTNDIST_TRAIN_LOG:-$ROOT/outputs_v2/training.log}"
PYTHON=""

info() {
  printf '[attn-dist] %s\n' "$*"
}

warn() {
  printf '[attn-dist] WARNING: %s\n' "$*" >&2
}

die() {
  printf '[attn-dist] ERROR: %s\n' "$*" >&2
  exit 1
}

find_python() {
  local candidate version
  if [[ -n "${PYTHON_BIN:-}" ]]; then
    command -v "$PYTHON_BIN" >/dev/null 2>&1 || die "PYTHON_BIN is not executable: $PYTHON_BIN"
    printf '%s\n' "$PYTHON_BIN"
    return
  fi
  for candidate in python3.12 python3.13 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
      version="$($candidate -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
      case "$version" in
        3.10|3.11|3.12|3.13)
          command -v "$candidate"
          return
          ;;
      esac
    fi
  done
  die "Python 3.10-3.13 is required. Python 3.12 is recommended."
}

venv_is_healthy() {
  [[ -f "$STAMP_FILE" ]] \
    && [[ -x "$VENV_DIR/bin/python" ]] \
    && "$VENV_DIR/bin/python" -c 'import sys' >/dev/null 2>&1
}

ensure_environment() {
  local system_python backup current_stamp saved_stamp
  system_python="$(find_python)"
  if [[ -d "$VENV_DIR" ]] && ! venv_is_healthy; then
    backup="$VENV_DIR.broken.$(date +%Y%m%d-%H%M%S)"
    warn "Existing virtual environment is unusable; preserving it at $backup"
    mv "$VENV_DIR" "$backup"
  fi
  if [[ ! -d "$VENV_DIR" ]]; then
    info "Creating Python environment at $VENV_DIR"
    "$system_python" -m venv "$VENV_DIR"
  fi
  PYTHON="$VENV_DIR/bin/python"
  current_stamp="$(cksum "$ROOT/pyproject.toml")"
  saved_stamp="$(cat "$STAMP_FILE" 2>/dev/null || true)"
  if [[ "$current_stamp" != "$saved_stamp" ]]; then
    info "Installing project dependencies"
    PIP_DISABLE_PIP_VERSION_CHECK=1 "$PYTHON" -m pip install --no-cache-dir --upgrade pip setuptools wheel
    (cd "$ROOT" && PIP_DISABLE_PIP_VERSION_CHECK=1 "$PYTHON" -m pip install --no-cache-dir -e '.[dev]')
    printf '%s\n' "$current_stamp" > "$STAMP_FILE"
  else
    info "Dependencies are current"
  fi
}

ensure_frontend() {
  local current_stamp saved_stamp
  command -v node >/dev/null 2>&1 || die "Node.js 20 or newer is required for the web UI"
  command -v npm >/dev/null 2>&1 || die "npm is required for the web UI"
  node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 20 ? 0 : 1)' \
    || die "Node.js 20 or newer is required for the web UI"
  current_stamp="$(cksum "$UI_DIR/package.json" "$UI_DIR/package-lock.json")"
  saved_stamp="$(cat "$UI_STAMP_FILE" 2>/dev/null || true)"
  if [[ ! -x "$UI_DIR/node_modules/.bin/vite" ]] || [[ "$current_stamp" != "$saved_stamp" ]]; then
    info "Installing web interface dependencies"
    (cd "$UI_DIR" && npm ci --no-audit --no-fund)
    printf '%s\n' "$current_stamp" > "$UI_STAMP_FILE"
  else
    info "Web interface dependencies are current"
  fi
}

find_free_port() {
  local start_port="$1"
  "$PYTHON" - "$start_port" <<'PY'
import socket
import sys

start = int(sys.argv[1])
for port in range(start, start + 100):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            continue
    print(port)
    break
else:
    raise SystemExit(f"No free port found between {start} and {start + 99}")
PY
}

has_dataset() {
  [[ -f "$ROOT/data/pannuke/images.npy" ]] \
    && [[ -f "$ROOT/data/pannuke/instances.npy" ]] \
    && [[ -f "$ROOT/data/pannuke/folds.npy" ]]
}

find_checkpoint() {
  local candidate
  for candidate in \
    "$ROOT/outputs_v2/checkpoints/best_iou_calibrated.pt" \
    "$ROOT/outputs_v2/checkpoints/best_iou.pt" \
    "$ROOT/outputs_v2/checkpoints/best_model.pth"; do
    if [[ -f "$candidate" ]] && checkpoint_is_valid "$candidate"; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  return 1
}

find_existing_checkpoint() {
  local candidate
  for candidate in \
    "$ROOT/outputs_v2/checkpoints/best_iou_calibrated.pt" \
    "$ROOT/outputs_v2/checkpoints/best_iou.pt" \
    "$ROOT/outputs_v2/checkpoints/best_model.pth"; do
    if [[ -f "$candidate" ]]; then
      printf '%s\n' "$candidate"
      return
    fi
  done
  return 1
}

checkpoint_is_valid() {
  local checkpoint="$1"
  (
    cd "$ROOT"
    "$PYTHON" -c \
      'import sys; from src.inference import AttnDistInference; AttnDistInference.from_checkpoint(sys.argv[1], "cpu")' \
      "$checkpoint"
  ) >/dev/null 2>&1
}

doctor() {
  local checkpoint
  ensure_environment
  info "Running environment diagnostics"
  "$PYTHON" -c 'import torch; print(f"Python/Torch ready: torch={torch.__version__}, cuda={torch.cuda.is_available()}, mps={torch.backends.mps.is_available()}")'
  "$PYTHON" -c 'import albumentations, fastapi, scipy, skimage, uvicorn; print("Runtime imports ready")'
  if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    info "Web runtime ready: node=$(node --version), npm=$(npm --version)"
  else
    warn "Node.js/npm are absent; the React workstation cannot start"
  fi
  if has_dataset; then
    info "Prepared PanNuke dataset found"
  else
    warn "Prepared PanNuke arrays are absent; training and evaluation are unavailable"
  fi
  if checkpoint="$(find_checkpoint)"; then
    info "Deployable checkpoint validated: $checkpoint"
  elif checkpoint="$(find_existing_checkpoint)"; then
    warn "Checkpoint exists but is incompatible with the deployable model contract: $checkpoint"
  else
    warn "No model checkpoint found; the app will open but analysis requires a checkpoint"
  fi
}

validate_data() {
  ensure_environment
  has_dataset || die "Missing data/pannuke/{images,instances,folds}.npy"
  (cd "$ROOT" && "$PYTHON" -m scripts.validate_dataset --require-complete)
}

prepare_data() {
  ensure_environment
  (cd "$ROOT" && "$PYTHON" -m scripts.prepare_pannuke "${@:2}" --preflight)
  info "Installing dataset preparation support"
  (cd "$ROOT" && PIP_DISABLE_PIP_VERSION_CHECK=1 "$PYTHON" -m pip install --no-cache-dir -e '.[data]')
  cd "$ROOT"
  exec "$PYTHON" -m scripts.prepare_pannuke "${@:2}"
}

check_project() {
  ensure_environment
  ensure_frontend
  info "Checking shell entrypoint"
  bash -n "$ROOT/setup.sh"
  info "Running Ruff"
  (cd "$ROOT" && "$PYTHON" -m ruff check src tests train.py evaluate.py api.py scripts)
  info "Running mypy"
  (cd "$ROOT" && "$PYTHON" -m mypy src train.py evaluate.py api.py scripts)
  info "Running tests"
  (cd "$ROOT" && MPLBACKEND=Agg "$PYTHON" -m pytest -p no:cacheprovider -q)
  info "Type-checking web interface"
  (cd "$UI_DIR" && npm run typecheck)
  info "Building web interface"
  (cd "$UI_DIR" && npm run build)
}

start_stack() {
  local api_port ui_port api_pid attempt api_ready=0
  doctor
  ensure_frontend
  api_port="$(find_free_port "${ATTNDIST_API_PORT:-8000}")"
  ui_port="$(find_free_port "${ATTNDIST_UI_PORT:-5173}")"
  if [[ "$ui_port" == "$api_port" ]]; then
    ui_port="$(find_free_port "$((ui_port + 1))")"
  fi
  info "Starting inference API at http://127.0.0.1:$api_port"
  (cd "$ROOT" && "$PYTHON" -m uvicorn api:app --host 127.0.0.1 --port "$api_port") &
  api_pid=$!
  cleanup() {
    if kill -0 "$api_pid" >/dev/null 2>&1; then
      kill "$api_pid" >/dev/null 2>&1 || true
      wait "$api_pid" 2>/dev/null || true
    fi
  }
  trap cleanup EXIT INT TERM
  for ((attempt = 0; attempt < 100; attempt++)); do
    if "$PYTHON" -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:$api_port/api/health', timeout=0.2)" >/dev/null 2>&1; then
      api_ready=1
      break
    fi
    if ! kill -0 "$api_pid" >/dev/null 2>&1; then
      wait "$api_pid" || true
      die "Inference API exited during startup"
    fi
    sleep 0.1
  done
  [[ "$api_ready" -eq 1 ]] || die "Inference API did not become ready within 10 seconds"
  info "Starting React workstation at http://127.0.0.1:$ui_port"
  (cd "$UI_DIR" && VITE_API_TARGET="http://127.0.0.1:$api_port" npm run dev -- --host 127.0.0.1 --port "$ui_port")
}

train_model() {
  ensure_environment
  has_dataset || die "Training requires prepared PanNuke arrays in data/pannuke"
  cd "$ROOT"
  exec "$PYTHON" "$ROOT/train.py" "${@:2}"
}

training_is_running() {
  local pid
  [[ -f "$TRAIN_PID_FILE" ]] || return 1
  pid="$(cat "$TRAIN_PID_FILE")"
  [[ "$pid" =~ ^[0-9]+$ ]] || return 1
  kill -0 "$pid" >/dev/null 2>&1 || return 1
  ps -p "$pid" -o command= | grep -F "$ROOT/train.py" >/dev/null 2>&1
}

start_training_background() {
  local pid
  ensure_environment
  has_dataset || die "Training requires prepared PanNuke arrays in data/pannuke"
  if training_is_running; then
    die "Training is already running with PID $(cat "$TRAIN_PID_FILE")"
  fi
  mkdir -p "$(dirname "$TRAIN_PID_FILE")" "$(dirname "$TRAIN_LOG_FILE")"
  info "Starting background training; log: $TRAIN_LOG_FILE"
  (
    cd "$ROOT"
    nohup "$PYTHON" "$ROOT/train.py" "${@:2}" >>"$TRAIN_LOG_FILE" 2>&1 &
    printf '%s\n' "$!" >"$TRAIN_PID_FILE"
  )
  pid="$(cat "$TRAIN_PID_FILE")"
  sleep 1
  training_is_running || die "Training failed to start; inspect $TRAIN_LOG_FILE"
  info "Training started with PID $pid"
}

training_status() {
  local pid elapsed
  if training_is_running; then
    pid="$(cat "$TRAIN_PID_FILE")"
    elapsed="$(ps -p "$pid" -o etime= | tr -d ' ')"
    info "Training is running: pid=$pid elapsed=$elapsed"
  else
    info "No training process is running"
  fi
  if [[ -f "$TRAIN_LOG_FILE" ]]; then
    info "Recent training output from $TRAIN_LOG_FILE"
    tail -n 12 "$TRAIN_LOG_FILE"
  fi
}

evaluate_model() {
  local checkpoint="${2:-}"
  ensure_environment
  has_dataset || die "Evaluation requires prepared PanNuke arrays in data/pannuke"
  if [[ -z "$checkpoint" ]]; then
    checkpoint="$(find_checkpoint)" || die "No checkpoint found"
  fi
  cd "$ROOT"
  exec "$PYTHON" "$ROOT/evaluate.py" "$checkpoint" "${@:3}"
}

tune_postprocessing() {
  local checkpoint="${2:-}"
  ensure_environment
  has_dataset || die "Postprocessing tuning requires prepared PanNuke arrays in data/pannuke"
  if [[ -z "$checkpoint" ]]; then
    checkpoint="$(find_checkpoint)" || die "No checkpoint found"
  fi
  cd "$ROOT"
  exec "$PYTHON" -m scripts.tune_postprocessing "$checkpoint" "${@:3}"
}

usage() {
  cat <<'EOF'
Usage: ./setup.sh [command] [arguments]

Commands:
  start                 Start the React workstation and inference API (default)
  setup                 Create/update Python and web environments only
  doctor                Verify runtime, dataset, and checkpoint availability
  check                 Run shell validation, lint, and all tests
  validate              Validate and hash prepared PanNuke arrays
  prepare-data [...]    Stream and prepare the pinned PanNuke release
  train [options]       Run train.py with the supplied options
  train-bg [options]    Start one guarded training run in the background
  training-status       Show background training state and recent output
  evaluate [path] [...] Evaluate a checkpoint, auto-discovering it when omitted
  tune [path] [...]     Tune postprocessing on validation fold 2 only
  all                   Run checks, validate data when present, then start the app
  help                  Show this message

Environment overrides:
  PYTHON_BIN, ATTNDIST_VENV_DIR, ATTNDIST_DATA_DIR, ATTNDIST_OUTPUT_DIR
  ATTNDIST_API_PORT, ATTNDIST_UI_PORT, ATTNDIST_CHECKPOINT
EOF
}

command="${1:-start}"
case "$command" in
  start) start_stack ;;
  setup)
    ensure_environment
    ensure_frontend
    ;;
  doctor) doctor ;;
  check) check_project ;;
  validate) validate_data ;;
  prepare-data) prepare_data "$@" ;;
  train) train_model "$@" ;;
  train-bg) start_training_background "$@" ;;
  training-status) training_status ;;
  evaluate) evaluate_model "$@" ;;
  tune) tune_postprocessing "$@" ;;
  all)
    check_project
    doctor
    if has_dataset; then
      validate_data
    fi
    start_stack
    ;;
  help|-h|--help) usage ;;
  *) usage; die "Unknown command: $command" ;;
esac
