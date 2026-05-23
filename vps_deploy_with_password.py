#!/usr/bin/env python3
"""One-shot deploy: ZIP staging + SFTP upload + remote setup via SSH/SFTP.

Secrets (either works):
  - File `vps_deploy_local.secret` in this folder: line1 = password,
    optional line2 = ssh user (root/ubuntu).
  - Environment: UTC_VPS_PASSWORD (optional UTC_VPS_USER, comma-separated).

Auto-retry until success (your PC / when SSH is blocked temporarily):
  set UTC_DEPLOY_UNTIL_OK=1
  optional: UTC_DEPLOY_RETRY_SEC=45  UTC_DEPLOY_MAX_MINUTES=480
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import paramiko


def _default_vps_host() -> str:
    cfg = Path(__file__).resolve().parent / "config" / "production.json"
    if cfg.is_file():
        try:
            data = json.loads(cfg.read_text(encoding="utf-8"))
            h = str(data.get("vps_host", "")).strip()
            if h:
                return h
        except (OSError, json.JSONDecodeError, TypeError):
            pass
    return "160.251.140.31"


HOST = os.environ.get("UTC_VPS_HOST", _default_vps_host())

REPO = Path(__file__).resolve().parent
SECRET_FILE = REPO / "vps_deploy_local.secret"
REMOTE_ZIP = "/tmp/utc_web.zip"
REMOTE_SH = "/tmp/vps_setup_utc_web.sh"
LOG_DIR = REPO / "logs"
EXCLUDE_DIRS = {"logs", ".git", "__pycache__", "_deploy_tmp", ".cursor"}
EXCLUDE_FILES = {
    "utc_web_deploy.zip",
    "cloudflared.exe",
    "ngrok.exe",
    "vps_deploy_local.secret",
    "cloudflare_dns_config.ps1",
}


def _safe_write(stream, text: str) -> None:
    if not text:
        return
    try:
        stream.write(text)
    except UnicodeEncodeError:
        buf = getattr(stream, "buffer", None)
        if buf is not None:
            buf.write(text.encode("utf-8", errors="replace"))


def load_credentials() -> tuple[str, list[str]]:
    pwd = os.environ.get("UTC_VPS_PASSWORD", "").strip()
    users_env = os.environ.get("UTC_VPS_USER", "").strip()
    users = (
        [u.strip() for u in users_env.split(",") if u.strip()]
        if users_env
        else ["root", "ubuntu"]
    )
    if not pwd and SECRET_FILE.is_file():
        try:
            raw = SECRET_FILE.read_text(encoding="utf-8")
        except OSError:
            raw = ""
        lines: list[str] = []
        for ln in raw.splitlines():
            s = ln.strip()
            if not s or s.startswith("#"):
                continue
            lines.append(s)
        if lines:
            pwd = lines[0]
        if len(lines) > 1 and lines[1].strip():
            users = [lines[1].strip()]
    return pwd, users


def stage_dir() -> Path:
    d = Path(tempfile.mkdtemp(prefix="utc_web_deploy_"))
    for p in REPO.iterdir():
        name = p.name
        if p.is_dir() and name in EXCLUDE_DIRS:
            continue
        if p.is_file() and name in EXCLUDE_FILES:
            continue
        dest = d / name
        if p.is_dir():
            shutil.copytree(p, dest, dirs_exist_ok=True, ignore=shutil.ignore_patterns("*.pyc"))
        else:
            shutil.copy2(p, dest)
    return d


def make_zip(stage: Path, zip_path: Path) -> None:
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for fp in stage.rglob("*"):
            if fp.is_file():
                arc = fp.relative_to(stage).as_posix()
                z.write(fp, arcname=arc)


def connect(user: str, password: str) -> paramiko.SSHClient:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        HOST,
        username=user,
        password=password,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )
    return c


def log_line(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"{ts} {msg}\n"
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (LOG_DIR / "deploy_auto.log").open("a", encoding="utf-8") as f:
            f.write(line)
    except OSError:
        pass
    print(msg, flush=True)


def deploy_once(password: str, user_candidates: list[str]) -> tuple[int, str]:
    """Returns (exit_code, reason_for_human). retry_ok if exit code 1."""
    zip_path = REPO / "utc_web_deploy.zip"
    setup_sh = REPO / "vps_setup_utc_web.sh"
    if not setup_sh.is_file():
        return 2, "missing vps_setup_utc_web.sh"

    print("[1/4] staging…")
    stage = stage_dir()
    try:
        print("[2/4] zip…")
        if zip_path.exists():
            zip_path.unlink()
        make_zip(stage, zip_path)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    last_err: BaseException | None = None
    saw_auth_fail = False
    saw_network_fail = False

    for user in [u.strip() for u in user_candidates if u.strip()]:
        try:
            print(f"[3/4] connect {user}@{HOST} …")
            client = connect(user, password)
        except paramiko.AuthenticationException:
            saw_auth_fail = True
            last_err = None
            print(f"  {user}: authentication failed")
            continue
        except BaseException as e:
            saw_network_fail = True
            last_err = e
            print(f"  {user}: {e}")
            continue
        try:
            sftp = client.open_sftp()
            print("  upload zip…")
            sftp.put(str(zip_path), REMOTE_ZIP)
            print("  upload setup…")
            sftp.put(str(setup_sh), REMOTE_SH)
            sftp.close()
            print("[4/4] remote setup…")
            stdin, stdout, stderr = client.exec_command(
                f"chmod +x {REMOTE_SH} && bash {REMOTE_SH}", get_pty=True
            )
            out = stdout.read().decode(errors="replace")
            err = stderr.read().decode(errors="replace")
            code = stdout.channel.recv_exit_status()
            _safe_write(sys.stdout, out)
            _safe_write(sys.stderr, err)
            try:
                zip_path.unlink(missing_ok=True)
            except OSError:
                pass
            print("DONE." if code == 0 else f"Remote exit {code}")
            if code != 0:
                return code, f"remote script exit {code}"
            return 0, "ok"
        finally:
            try:
                client.close()
            except Exception:
                pass

    print("All SSH users failed.", file=sys.stderr)
    print(
        "Hint: attach security group with IN TCP 22 / 80 / 443 on this VPS in ConoHa.",
        file=sys.stderr,
    )
    if last_err:
        print(last_err, file=sys.stderr)

    if saw_auth_fail and not saw_network_fail:
        return 4, "ssh authentication failed for all users (check password / user line2)"
    return 1, "network or ssh unreachable"


def main() -> int:
    password, user_candidates = load_credentials()
    if not password:
        print(
            "Missing VPS password. Run SAVE_VPS_SECRET_ONCE.bat once.",
            file=sys.stderr,
        )
        return 2

    until_ok = os.environ.get("UTC_DEPLOY_UNTIL_OK", "").lower() in ("1", "true", "yes")
    retry_sec = float(os.environ.get("UTC_DEPLOY_RETRY_SEC", "45"))
    max_min = os.environ.get("UTC_DEPLOY_MAX_MINUTES", "").strip()
    max_until = time.monotonic() + (float(max_min) * 60.0) if max_min else None

    attempt = 0
    while True:
        attempt += 1
        log_line(f"deploy attempt {attempt} → {HOST}")
        code, reason = deploy_once(password, user_candidates)

        if code == 0:
            log_line("deploy SUCCESS")
            return 0

        if code == 2:
            log_line(f"deploy ABORT ({reason}), no retry")
            return code

        if code == 4:
            log_line(f"deploy ABORT ({reason}), wrong password/user — fix secret file")
            return code

        if not until_ok:
            log_line(f"deploy FAIL ({reason}) code={code}")
            return code

        if max_until is not None and time.monotonic() >= max_until:
            log_line(f"deploy STOPPED (UTC_DEPLOY_MAX_MINUTES elapsed) last={reason}")
            return code

        log_line(f"will retry in {retry_sec}s … ({reason})")
        time.sleep(retry_sec)


if __name__ == "__main__":
    raise SystemExit(main())
