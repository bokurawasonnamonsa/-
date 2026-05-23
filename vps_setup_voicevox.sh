#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/opt/voicevox_engine"
BIN_LINK="/usr/local/bin/voicevox_engine"
SERVICE_PATH="/etc/systemd/system/voicevox-engine.service"
PORT="${VOICEVOX_PORT:-50021}"

export DEBIAN_FRONTEND=noninteractive
apt update
apt -y install curl ca-certificates python3 p7zip-full

mkdir -p "$APP_DIR"
cd "$APP_DIR"

python3 - <<'PY'
import json
import re
import sys
import urllib.request
from pathlib import Path

api = "https://api.github.com/repos/VOICEVOX/voicevox_engine/releases/latest"
with urllib.request.urlopen(api, timeout=30) as res:
    release = json.loads(res.read().decode("utf-8"))

prefix = None
parts = []
for a in release.get("assets", []):
    name = a.get("name", "")
    if re.match(r"voicevox_engine-linux-cpu-x64-.*\.7z\.001$", name):
        prefix = name[:-3]
        break

if not prefix:
    print("ERROR: CPU x64 7z package not found.", file=sys.stderr)
    sys.exit(2)

for a in release.get("assets", []):
    name = a.get("name", "")
    if name.startswith(prefix):
        parts.append({"name": name, "url": a.get("browser_download_url", "")})

parts.sort(key=lambda x: x["name"])
if not parts:
    print("ERROR: package parts not found.", file=sys.stderr)
    sys.exit(2)

Path("release_name.txt").write_text(release.get("tag_name", "unknown"), encoding="utf-8")
Path("asset_prefix.txt").write_text(prefix, encoding="utf-8")
Path("asset_parts.json").write_text(json.dumps(parts, ensure_ascii=False, indent=2), encoding="utf-8")
PY

ASSET_PREFIX="$(cat asset_prefix.txt)"

rm -rf "${APP_DIR}/engine" "${APP_DIR}/tmp_extract"
mkdir -p "${APP_DIR}/tmp_extract"
python3 - <<'PY'
import json
import subprocess
from pathlib import Path

parts = json.loads(Path("asset_parts.json").read_text(encoding="utf-8"))
for p in parts:
    if not p.get("url"):
        raise SystemExit("missing part url")
    out = Path(p["name"])
    subprocess.check_call(["curl", "-fL", p["url"], "-o", str(out)])
PY

FIRST_PART="${APP_DIR}/${ASSET_PREFIX}001"
7z x -y "${FIRST_PART}" "-o${APP_DIR}/tmp_extract" >/dev/null

ENGINE_DIR="$(python3 - <<'PY'
from pathlib import Path
p = Path("/opt/voicevox_engine/tmp_extract")
dirs = [x for x in p.iterdir() if x.is_dir()]
print(str(dirs[0]) if dirs else "")
PY
)"
if [[ -z "${ENGINE_DIR}" ]]; then
  echo "ERROR: extracted engine directory not found" >&2
  exit 2
fi

mv "${ENGINE_DIR}" "${APP_DIR}/engine"
chmod +x "${APP_DIR}/engine/run" || true
ln -sf "${APP_DIR}/engine/run" "${BIN_LINK}"

cat >"${SERVICE_PATH}" <<EOF
[Unit]
Description=VOICEVOX Engine (CPU)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}/engine
ExecStart=${APP_DIR}/engine/run --host 127.0.0.1 --port ${PORT}
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable voicevox-engine
systemctl restart voicevox-engine
systemctl is-active voicevox-engine

curl -fsS "http://127.0.0.1:${PORT}/version" || true
echo
echo "VOICEVOX setup done."
