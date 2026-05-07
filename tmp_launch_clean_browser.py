import os
import shutil
import subprocess
import tempfile

candidates = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
]

exe = next((p for p in candidates if os.path.exists(p)), None)
if not exe:
    print("NO_BROWSER_EXE")
    raise SystemExit(1)

profile = os.path.join(tempfile.gettempdir(), "utc_web_fresh_profile")
shutil.rmtree(profile, ignore_errors=True)
os.makedirs(profile, exist_ok=True)

subprocess.Popen([exe, f"--user-data-dir={profile}", "--disable-extensions", "https://3301-svs.jp"])
print(f"LAUNCHED:{exe}")
