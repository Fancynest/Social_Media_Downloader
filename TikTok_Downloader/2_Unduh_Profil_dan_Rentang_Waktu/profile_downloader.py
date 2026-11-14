# -*- coding: utf-8 -*-
"""
TikTok Profile & Date Range Downloader
======================================
Mengunduh seluruh video dari akun TikTok dengan dukungan filter rentang
tanggal postingan dan pengelompokan folder otomatis per profil / kreator.
"""

import os
import sys
import re
import shutil
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
COOKIE_INPUT = BASE_DIR / "input_cookie.txt"
COOKIE_ACTIVE = BASE_DIR / ".cookies_active.txt"
COOKIE_DIRECT = BASE_DIR / "cookies.txt"


def prepare_clean_cookie_file() -> Path | None:
    candidate_inputs = [COOKIE_INPUT, BASE_DIR.parent / "input_cookie.txt"]
    for c_in in candidate_inputs:
        if c_in.exists() and c_in.stat().st_size > 20:
            raw_text = c_in.read_text(encoding="utf-8", errors="ignore").strip()
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
                                entries.append(f".tiktok.com\tTRUE\t/\tTRUE\t2147483647\t{k}\t{v}")
                    if entries:
                        clean_content = "# Netscape HTTP Cookie File\n" + "\n".join(entries) + "\n"
                    else:
                        clean_content = "# Netscape HTTP Cookie File\n" + raw_text + "\n"

                COOKIE_ACTIVE.write_text(clean_content, encoding="utf-8")
                return COOKIE_ACTIVE

    for c_dir in [COOKIE_DIRECT, BASE_DIR.parent / "cookies.txt"]:
        if c_dir.exists() and c_dir.stat().st_size > 20:
            return c_dir

    return None


def extract_profile_info(raw: str) -> tuple[str, str]:
    """Mengembalikan tuple (username_bersih, url_lengkap)."""
    cleaned = raw.strip()
    if "?" in cleaned:
        cleaned = cleaned.split("?")[0]
    cleaned = cleaned.rstrip("/")

    # Format: @username
    if cleaned.startswith("@"):
        user = cleaned[1:].strip()
        return user, f"https://www.tiktok.com/@{user}"

    # Format: https://www.tiktok.com/@username
    m = re.search(r'tiktok\.com/@([a-zA-Z0-9_\.]{1,50})', cleaned)
    if m:
        user = m.group(1)
        return user, f"https://www.tiktok.com/@{user}"

    # Format: username polos
    if re.match(r'^[a-zA-Z0-9_\.]{2,50}$', cleaned):
        return cleaned, f"https://www.tiktok.com/@{cleaned}"

    return cleaned, cleaned


def parse_date_str(val: str) -> str:
    cleaned = re.sub(r"[^\d]", "", val.strip())
    if len(cleaned) == 8:
        return cleaned
    return ""


def load_profiles_and_settings():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write(
                "# =====================================================================\n"
                "# PENGATURAN TARGET PROFIL TIKTOK & RENTANG WAKTU\n"
                "# =====================================================================\n"
                "DARI_TANGGAL=\n"
                "SAMPAI_TANGGAL=\n\n"
                "# TEMPELKAN TARGET PROFIL DI BAWAH INI:\n"
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

            user, url = extract_profile_info(line)
            if user and not any(p[0] == user for p in profiles):
                profiles.append((user, url))

    return profiles, dari_tanggal, sampai_tanggal


def download_profile_with_gallery_dl(user: str, dest_dir: Path, cookie_file: Path | None) -> bool:
    target_url = f"https://www.tiktok.com/@{user}"
    cmd = [
        sys.executable, "-m", "gallery_dl",
        "-d", str(dest_dir),
        "--download-archive", str(ARCHIVE_FILE),
        "--no-mtime",
        target_url
    ]
    if cookie_file:
        cmd.extend(["--cookies", str(cookie_file)])
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", timeout=300)
        return proc.returncode == 0
    except Exception:
        return False


def main():
    print("=" * 65)
    print("       TIKTOK PROFILE & DATE RANGE DOWNLOADER")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profiles, dari_tanggal, sampai_tanggal = load_profiles_and_settings()

    if not profiles:
        print(f"\n[!] Belum ada target akun pada '{TXT_FILE.name}'.")
        print(f"    Silakan buka '{TXT_FILE.name}' atau klik 'BUKA_NOTEPAD_TARGET.bat'")
        print("    lalu tempelkan tautan atau username TikTok yang ingin diunduh.")
        return

    print(f"[*] Ditemukan {len(profiles)} profil TikTok target:")
    for user, url in profiles:
        print(f"    - @{user} ({url})")

    d_info = f"{dari_tanggal[:4]}-{dari_tanggal[4:6]}-{dari_tanggal[6:]}" if dari_tanggal else "Awal Akun"
    s_info = f"{sampai_tanggal[:4]}-{sampai_tanggal[4:6]}-{sampai_tanggal[6:]}" if sampai_tanggal else "Terbaru"
    print(f"[*] Filter Tanggal Video: {d_info} s/d {s_info}")

    cookie_file = prepare_clean_cookie_file()
    if cookie_file:
        print(f"[*] Menggunakan file cookies: {cookie_file.name}")
    else:
        print("[*] Berjalan dalam mode anonim (tanpa cookies).")

    try:
        import yt_dlp
    except ImportError:
        import subprocess
        print("\n[*] Library 'yt-dlp' belum terpasang. Memasang otomatis...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp>=2024.0.0"])
            import yt_dlp
            print("[✓] Library 'yt-dlp' berhasil dipasang!\n")
        except Exception as e:
            print(f"[x] Gagal memasang otomatis: {e}")
            print("    Silakan jalankan: pip install -r requirements.txt")
            return

    has_ffmpeg = shutil.which("ffmpeg") is not None
    print("\n[*] Memulai proses pengunduhan profil...")
    print("-" * 65)

    total_profiles = len(profiles)
    success = 0

    for idx, (user, url) in enumerate(profiles, start=1):
        print(f"\n[{idx}/{total_profiles}] Memproses profil @{user}: {url}")
        dest_dir = OUTPUT_DIR / f"@{user}"
        dest_dir.mkdir(parents=True, exist_ok=True)

        outtmpl = str(dest_dir / "%(upload_date|NA)s - %(title).80s [%(id)s].%(ext)s")

        ydl_opts = {
            "format": "best",
            "outtmpl": outtmpl,
            "merge_output_format": "mp4" if has_ffmpeg else None,
            "download_archive": str(ARCHIVE_FILE),
            "ignoreerrors": True,
            "no_warnings": False,
            "quiet": False,
            "noplaylist": False,
        }

        if dari_tanggal:
            ydl_opts["dateafter"] = dari_tanggal
        if sampai_tanggal:
            ydl_opts["datebefore"] = sampai_tanggal
        if cookie_file:
            ydl_opts["cookiefile"] = str(cookie_file)

        downloaded = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ret = ydl.download([url])
                if ret == 0:
                    downloaded = True
        except Exception as e:
            print(f"     [!] yt-dlp kendala ({e})")

        if not downloaded:
            print(f"     [*] Mencoba unduh profil @{user} via gallery-dl...")
            if download_profile_with_gallery_dl(user, dest_dir, cookie_file):
                print(f"     [✓] Berhasil diunduh via gallery-dl!")
                downloaded = True

        if downloaded:
            success += 1
        else:
            print(f"     [x] Gagal memproses profil: @{user}")

    print("\n" + "=" * 65)
    print(f"[✓] Selesai! Berhasil memproses {success}/{total_profiles} profil.")
    print(f"[✓] Seluruh video tersimpan di folder: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
