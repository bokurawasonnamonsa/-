#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
from pathlib import Path

import paramiko

HOST = os.environ.get("UTC_VPS_HOST", "160.251.140.31")
REPO = Path(__file__).resolve().parent
SECRET_FILE = REPO / "vps_deploy_local.secret"
LOCAL_SH = REPO / "vps_setup_voicevox.sh"
REMOTE_SH = "/tmp/vps_setup_voicevox.sh"


def load_credentials() -> tuple[str, str]:
    pwd = os.environ.get("UTC_VPS_PASSWORD", "").strip()
    user = os.environ.get("UTC_VPS_USER", "").strip() or "root"
    if (not pwd) and SECRET_FILE.is_file():
        raw = SECRET_FILE.read_text(encoding="utf-8", errors="replace")
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip() and not ln.strip().startswith("#")]
        if lines:
            pwd = lines[0]
        if len(lines) > 1:
            user = lines[1]
    return pwd, user


def main() -> int:
    if not LOCAL_SH.is_file():
        print("missing vps_setup_voicevox.sh", file=sys.stderr)
        return 2

    password, user = load_credentials()
    if not password:
        print("missing VPS password (run SAVE_VPS_SECRET_ONCE.bat first)", file=sys.stderr)
        return 2

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cli.connect(
        HOST,
        username=user,
        password=password,
        timeout=30,
        banner_timeout=30,
        auth_timeout=30,
        allow_agent=False,
        look_for_keys=False,
    )
    try:
        sftp = cli.open_sftp()
        # Windows checkout may be CRLF; force LF before running on bash.
        sh_text = LOCAL_SH.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
        with sftp.file(REMOTE_SH, "w") as rf:
            rf.write(sh_text)
        sftp.close()

        cmd = f"chmod +x {REMOTE_SH} && bash {REMOTE_SH}"
        _stdin, stdout, stderr = cli.exec_command(cmd, get_pty=True)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        code = stdout.channel.recv_exit_status()
        sys.stdout.write(out)
        sys.stderr.write(err)
        print(f"\nexit={code}")
        return code
    finally:
        cli.close()


if __name__ == "__main__":
    raise SystemExit(main())
