#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'USAGE'
Usage: scripts/test_debian.sh [options]

Options:
  --install-system-deps  Install Debian packages with apt-get before testing.
  --live-crawler         Also run tests that access the school website.
  --no-venv              Use the current Python environment instead of .venv.
  -h, --help             Show this help message.

Environment:
  PYTHON_BIN             Python executable to use. Defaults to python3.
  VENV_DIR               Virtualenv directory. Defaults to .venv.
USAGE
}

log() {
  printf '\n[%s] %s\n' "$(date +%H:%M:%S)" "$*"
}

die() {
  printf 'Error: %s\n' "$*" >&2
  exit 1
}

INSTALL_SYSTEM_DEPS=0
LIVE_CRAWLER=0
USE_VENV=1

while [ "$#" -gt 0 ]; do
  case "$1" in
    --install-system-deps)
      INSTALL_SYSTEM_DEPS=1
      ;;
    --live-crawler)
      LIVE_CRAWLER=1
      ;;
    --no-venv)
      USE_VENV=0
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "Unknown option: $1"
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
cd "${REPO_ROOT}"

if [ -r /etc/os-release ]; then
  . /etc/os-release
  case "${ID:-}" in
    debian|ubuntu|linuxmint|pop)
      ;;
    *)
      case "${ID_LIKE:-}" in
        *debian*|*ubuntu*)
          ;;
        *)
          die "This script is intended for Debian-compatible systems. Detected ID=${ID:-unknown} ID_LIKE=${ID_LIKE:-unknown}."
          ;;
      esac
      ;;
  esac
else
  die "Cannot read /etc/os-release; run this on Debian or a Debian-compatible system."
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

if [ "${INSTALL_SYSTEM_DEPS}" -eq 1 ]; then
  command -v apt-get >/dev/null 2>&1 || die "apt-get is required for --install-system-deps."

  APT_PREFIX=""
  if [ "$(id -u)" -ne 0 ]; then
    command -v sudo >/dev/null 2>&1 || die "sudo is required when not running as root."
    APT_PREFIX="sudo"
  fi

  log "Installing Debian system dependencies"
  ${APT_PREFIX} apt-get update
  ${APT_PREFIX} apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    chromium \
    chromium-driver \
    ca-certificates
fi

command -v "${PYTHON_BIN}" >/dev/null 2>&1 || die "Python executable not found: ${PYTHON_BIN}"

if [ "${USE_VENV}" -eq 1 ]; then
  log "Preparing virtual environment: ${VENV_DIR}"
  "${PYTHON_BIN}" -m venv "${VENV_DIR}"
  # shellcheck disable=SC1091
  . "${VENV_DIR}/bin/activate"
  PYTHON_BIN="python"
fi

log "Installing Python dependencies"
"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install -r requirements.txt

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1
export CHROME_BIN="${CHROME_BIN:-/usr/bin/chromium}"
export CHROMEDRIVER_PATH="${CHROMEDRIVER_PATH:-/usr/bin/chromedriver}"

if [ "${LIVE_CRAWLER}" -eq 1 ]; then
  export RUN_LIVE_CRAWLER_TEST=1
  log "Running unittest suite with live crawler test enabled"
else
  unset RUN_LIVE_CRAWLER_TEST || true
  log "Running offline unittest suite"
fi

"${PYTHON_BIN}" -m unittest discover -s tests

log "Debian test flow completed"
