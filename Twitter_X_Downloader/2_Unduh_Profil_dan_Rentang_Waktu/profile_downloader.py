# -*- coding: utf-8 -*-
"""
Twitter / X Profile & Date Range Downloader
===========================================
Mengunduh seluruh media (foto resolusi asli & video kualitas tertinggi)
dari profil X / Twitter dengan filter rentang waktu (tanggal awal & akhir).
"""

import os
import sys
import re
import shutil
import subprocess
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
TXT_FILE = BASE_DIR / "target_profil.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
ARCHIVE_FILE = BASE_DIR / "download_history.txt"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
COOKIE_ACTIVE = BASE_DIR / ".cookies_active.txt"


def find_gallery_dl() -> list:
    """Mencari executable gallery-dl atau python -m gallery_dl."""
    bin_path = shutil.which("gallery-dl")
    if bin_path:
        return [bin_path]
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for match in winget_path.glob("**/gallery-dl.exe"):
        if match.is_file():
            return [str(match)]

    try:
        import gallery_dl
    except ImportError:
        print("[*] Memasang library 'gallery-dl' secara otomatis...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "gallery-dl>=1.27.0"])
        except Exception:
            pass

    return [sys.executable, "-m", "gallery_dl"]


def extract_username(raw: str) -> str | None:
    cleaned = raw.strip()
    if cleaned.startswith("@"):
        return cleaned.lstrip("@").strip("/")
    m = re.match(r'https?://(?:www\.)?(?:x|twitter)\.com/([a-zA-Z0-9_]{1,30})/?$', cleaned)
    if m and m.group(1).lower() not in ("home", "explore", "notifications", "messages", "settings", "search", "i"):
        return m.group(1)
    m2 = re.match(r'https?://(?:www\.)?(?:x|twitter)\.com/([a-zA-Z0-9_]{1,30})/media/?$', cleaned)
    if m2:
        return m2.group(1)
    if re.match(r'^[a-zA-Z0-9_]{1,30}$', cleaned):
        return cleaned
    return None


def parse_date_str(val: str) -> str:
    cleaned = re.sub(r"[^\d]", "", val.strip())
    if len(cleaned) == 8:
        return f"{cleaned[:4]}-{cleaned[4:6]}-{cleaned[6:]}"
    return ""


def prepare_clean_cookie_file() -> Path | None:
    candidate_inputs = [COOKIE_FILE, BASE_DIR.parent / "input_cookie.txt"]
    for c_file in candidate_inputs:
        if c_file.exists() and c_file.stat().st_size > 20:
            raw_text = c_file.read_text(encoding="utf-8", errors="ignore").strip()
            lines = [l for l in raw_text.splitlines() if l.strip() and not l.strip().startswith("#")]
            if lines:
                if any("\t" in l for l in lines) or any("# netscape" in l.lower() for l in raw_text.splitlines()):
                    idx = raw_text.find("# Netscape")
                    clean_content = (raw_text[idx:] if idx != -1 else "# Netscape HTTP Cookie File\n" + raw_text).strip() + "\n"
                else:
                    cookie_str = raw_text
                    if cookie_str.lower().startswith("cookie:"):
                        cookie_str = cookie_str[7:].strip()
                    tokens = [t.strip() for t in cookie_str.replace("\n", ";").split(";") if t.strip()]
                    entries = []
                    for token in tokens:
                        if "=" in token:
                            k, v = token.split("=", 1)
                            k, v = k.strip(), v.strip()
                            if k and not k.startswith("#"):
                                entries.append(f".x.com\tTRUE\t/\tTRUE\t2147483647\t{k}\t{v}")
                                entries.append(f".twitter.com\tTRUE\t/\tTRUE\t2147483647\t{k}\t{v}")
                    if entries:
                        clean_content = "# Netscape HTTP Cookie File\n" + "\n".join(entries) + "\n"
                    else:
                        clean_content = "# Netscape HTTP Cookie File\n" + raw_text + "\n"

                COOKIE_ACTIVE.write_text(clean_content, encoding="utf-8")
                return COOKIE_ACTIVE
    return None


def load_profiles_and_settings():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write(
                "# PENGATURAN TARGET PROFIL X / TWITTER & RENTANG WAKTU\n"
                "DARI_TANGGAL=\n"
                "SAMPAI_TANGGAL=\n\n"
                "# Masukkan tautan profil X/Twitter di bawah ini:\n"
            )
        return [], "", ""

    profiles = []
    dari_tanggal = ""
    sampai_tanggal = ""

    with open(TXT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            upper = line.upper()
            if upper.startswith("DARI_TANGGAL="):
                val = line.split("=", 1)[1]
                dari_tanggal = parse_date_str(val)
                continue
            if upper.startswith("SAMPAI_TANGGAL="):
                val = line.split("=", 1)[1]
                sampai_tanggal = parse_date_str(val)
                continue

            u = extract_username(line)
            if u and u not in profiles:
                profiles.append(u)

    return profiles, dari_tanggal, sampai_tanggal


def download_profile(username: str, dari_tanggal: str, sampai_tanggal: str, cookie_file: Path | None, gdl_cmd: list) -> bool:
    target_url = f"https://x.com/{username}/media"
    dest_dir = OUTPUT_DIR / username
    dest_dir.mkdir(parents=True, exist_ok=True)

    cmd = list(gdl_cmd)
    cmd.extend([
        "-d", str(dest_dir),
        "--download-archive", str(ARCHIVE_FILE),
        "--no-mtime",
    ])

    filter_exprs = []
    if dari_tanggal:
        filter_exprs.append(f"date >= '{dari_tanggal}'")
    if sampai_tanggal:
        filter_exprs.append(f"date <= '{sampai_tanggal} 23:59:59'")

    if filter_exprs:
        full_filter = " and ".join(filter_exprs)
        cmd.extend(["--filter", full_filter])

    if cookie_file:
        cmd.extend(["--cookies", str(cookie_file)])

    cmd.append(target_url)

    print(f"[*] Menjalankan unduhan media untuk @{username} ...")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
        for line in proc.stdout:
            s_line = line.strip()
            if s_line:
                if "#" in s_line or "Downloading" in s_line or ".mp4" in s_line or ".jpg" in s_line or ".png" in s_line:
                    print(f"    {s_line}")
        proc.wait()
        return proc.returncode == 0
    except Exception as e:
        print(f"[x] Kendala saat menjalankan gallery-dl: {e}")
        return False


def main():
    print("=" * 65)
    print("     TWITTER / X PROFILE & DATE RANGE DOWNLOADER")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profiles, dari_tanggal, sampai_tanggal = load_profiles_and_settings()

    if not profiles:
        print(f"\n[!] Belum ada target profil pada '{TXT_FILE.name}'.")
        print(f"    Silakan buka '{TXT_FILE.name}' atau klik 'BUKA_NOTEPAD_TARGET.bat'")
        print("    lalu tempelkan tautan profil yang ingin diunduh.")
        return

    print(f"[*] Ditemukan {len(profiles)} akun profil target:")
    for u in profiles:
        print(f"    - @{u}")

    d_info = dari_tanggal if dari_tanggal else "Awal Akun"
    s_info = sampai_tanggal if sampai_tanggal else "Terbaru"
    print(f"[*] Filter Tanggal Media: {d_info} s/d {s_info}")

    cookie_file = prepare_clean_cookie_file()
    if cookie_file:
        print(f"[*] Menggunakan file cookies: {cookie_file.name}")
    else:
        print("[*] Berjalan dalam mode publik anonim (tanpa cookies).")

    gdl_cmd = find_gallery_dl()
    print("-" * 65)

    total = len(profiles)
    success = 0

    for idx, u in enumerate(profiles, start=1):
        print(f"\n[{idx}/{total}] Memproses profil: @{u}")
        ok = download_profile(u, dari_tanggal, sampai_tanggal, cookie_file, gdl_cmd)
        if ok:
            success += 1

    print("\n" + "=" * 65)
    print(f"[✓] Selesai! Berhasil memproses {success}/{total} profil.")
    print(f"[✓] Seluruh berkas tersimpan di folder: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
