#!/usr/bin/env bash
# provision-server.sh — prepare bare Ubuntu machine to run cheat-buster server
# Run as root (or with sudo) from repo root: sudo bash bin/provision-server.sh
set -euo pipefail

# ---------- config ----------
APP_USER="${APP_USER:-cheatbuster}"
APP_DIR="${APP_DIR:-/opt/cheat-buster}"
SERVER_PORT="${SERVER_PORT:-80}"
PYTHON_VERSION="3.11"
SERVICE_NAME="cheat-buster"
# ----------------------------

info()  { echo "[INFO]  $*"; }
warn()  { echo "[WARN]  $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

[[ $EUID -eq 0 ]] || die "Run as root: sudo bash bin/provision-server.sh"

# ── 1. system packages ──────────────────────────────────────────────────────
info "Updating apt and installing system dependencies..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq \
    software-properties-common \
    curl \
    git \
    ca-certificates \
    build-essential

# Python 3.11 via deadsnakes PPA (covers Ubuntu 20.04/22.04/24.04)
if ! python3.11 --version &>/dev/null 2>&1; then
    info "Adding deadsnakes PPA for Python ${PYTHON_VERSION}..."
    add-apt-repository -y ppa:deadsnakes/ppa
    apt-get update -qq
    apt-get install -y -qq python3.11 python3.11-venv python3.11-dev
else
    info "Python ${PYTHON_VERSION} already installed."
fi

# ── 2. uv ────────────────────────────────────────────────────────────────────
if ! command -v uv &>/dev/null; then
    info "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # make available system-wide
    ln -sf "$HOME/.local/bin/uv" /usr/local/bin/uv
else
    info "uv already installed: $(uv --version)"
fi

# ── 3. app user ───────────────────────────────────────────────────────────────
if ! id "$APP_USER" &>/dev/null; then
    info "Creating system user: ${APP_USER}..."
    useradd --system --no-create-home --shell /usr/sbin/nologin "$APP_USER"
else
    info "User ${APP_USER} already exists."
fi

# ── 4. app directory ──────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SERVER_SRC="$REPO_ROOT/server"

[[ -d "$SERVER_SRC" ]] || die "server/ directory not found at $SERVER_SRC"

info "Syncing app files to ${APP_DIR}..."
mkdir -p "$APP_DIR"
rsync -a --delete \
    "$SERVER_SRC/app/" "$APP_DIR/app/" \
    --exclude '__pycache__' --exclude '*.pyc'
rsync -a --delete \
    "$SERVER_SRC/alembic/" "$APP_DIR/alembic/"
cp "$SERVER_SRC/alembic.ini" "$APP_DIR/alembic.ini"
cp "$SERVER_SRC/pyproject.toml" "$APP_DIR/pyproject.toml"

mkdir -p "$APP_DIR/data"

# ── 5. .env ───────────────────────────────────────────────────────────────────
ENV_FILE="$APP_DIR/.env"
if [[ ! -f "$ENV_FILE" ]]; then
    info "Creating .env from template — set SECRET_KEY before production use!"
    cat > "$ENV_FILE" <<EOF
DATABASE_URL=sqlite+aiosqlite:////opt/cheat-buster/data/cheat_buster.db
SECRET_KEY=$(python3.11 -c "import secrets; print(secrets.token_hex(32))")
ALGORITHM=HS256
EOF
    warn "Generated random SECRET_KEY. Verify ${ENV_FILE} before starting service."
else
    info ".env already exists, skipping creation."
fi

# ── 6. virtual environment & dependencies ────────────────────────────────────
VENV="$APP_DIR/.venv"
if [[ ! -d "$VENV" ]]; then
    info "Creating venv with Python ${PYTHON_VERSION}..."
    uv venv --python python3.11 "$VENV"
fi

info "Installing Python dependencies..."
uv pip install --python "$VENV/bin/python" \
    --project "$APP_DIR" \
    --no-editable \
    "$APP_DIR" 2>/dev/null \
    || uv pip install --python "$VENV/bin/python" -e "$APP_DIR"

# ── 7. database migrations ───────────────────────────────────────────────────
info "Running Alembic migrations..."
(
    cd "$APP_DIR"
    set -a; source "$ENV_FILE"; set +a
    "$VENV/bin/alembic" upgrade head
)

# ── 8. file ownership ─────────────────────────────────────────────────────────
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ── 9. systemd service ───────────────────────────────────────────────────────
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
info "Installing systemd service: ${SERVICE_NAME}..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=Cheat-Buster API Server
After=network.target

[Service]
Type=simple
User=${APP_USER}
WorkingDirectory=${APP_DIR}
EnvironmentFile=${ENV_FILE}
ExecStart=${VENV}/bin/uvicorn app.main:app --host 0.0.0.0 --port ${SERVER_PORT}
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=${SERVICE_NAME}

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"

# ── 10. summary ───────────────────────────────────────────────────────────────
info "Done. Service status:"
systemctl status "$SERVICE_NAME" --no-pager -l || true
echo
echo "  Manage:  systemctl {start,stop,restart,status} ${SERVICE_NAME}"
echo "  Logs:    journalctl -u ${SERVICE_NAME} -f"
echo "  Config:  ${ENV_FILE}"
echo "  Data:    ${APP_DIR}/data/"
