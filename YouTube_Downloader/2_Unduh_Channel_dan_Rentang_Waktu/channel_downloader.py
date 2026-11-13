# -*- coding: utf-8 -*-
"""
YouTube Channel & Date Range Downloader
=======================================
Mengunduh seluruh video dari channel YouTube dengan dukungan filter rentang
tanggal rilis (upload date) dan pengelompokan folder otomatis per channel.
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
TXT_FILE = BASE_DIR / "target_channel.txt"
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
                                entries.append(f".youtube.com\tTRUE\t/\tTRUE\t2147483647\t{k}\t{v}")
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


def clean_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("@"):
        return f"https://www.youtube.com/{url}"
    return url


def parse_date_str(val: str) -> str:
    cleaned = re.sub(r"[^\d]", "", val.strip())
    if len(cleaned) == 8:
        return cleaned
    return ""


def load_channels_and_settings():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write(
                "# PENGATURAN TARGET CHANNEL YOUTUBE & RENTANG WAKTU\n"
                "DARI_TANGGAL=\n"
                "SAMPAI_TANGGAL=\n\n"
                "# Masukkan link channel YouTube di bawah ini:\n"
            )
        return [], "", ""

    channels = []
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

            channels.append(clean_url(line))

    return channels, dari_tanggal, sampai_tanggal


def main():
    print("=" * 65)
    print("      YOUTUBE CHANNEL & DATE RANGE DOWNLOADER")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    channels, dari_tanggal, sampai_tanggal = load_channels_and_settings()

    if not channels:
        print(f"\n[!] Belum ada link channel pada '{TXT_FILE.name}'.")
        print(f"    Silakan buka '{TXT_FILE.name}' atau klik 'BUKA_NOTEPAD_TARGET.bat'")
        print("    lalu tempelkan tautan channel YouTube yang ingin diunduh.")
        return

    print(f"[*] Ditemukan {len(channels)} channel YouTube target:")
    for ch in channels:
        print(f"    - {ch}")

    d_info = f"{dari_tanggal[:4]}-{dari_tanggal[4:6]}-{dari_tanggal[6:]}" if dari_tanggal else "Awal Channel"
    s_info = f"{sampai_tanggal[:4]}-{sampai_tanggal[4:6]}-{sampai_tanggal[6:]}" if sampai_tanggal else "Terbaru"
    print(f"[*] Filter Tanggal Upload: {d_info} s/d {s_info}")

    cookie_file = prepare_clean_cookie_file()
    if cookie_file:
        print(f"[*] Menggunakan file cookies: {cookie_file.name}")
    else:
        print("[*] Berjalan dalam mode anonim (tanpa cookies).")

    has_ffmpeg = shutil.which("ffmpeg") is not None
    if has_ffmpeg:
        format_spec = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"
    else:
        format_spec = "best[ext=mp4]/best"
        print("[!] FFmpeg tidak terdeteksi di PATH. Mengunduh format gabungan tunggal.")

    try:
        import yt_dlp
    except ImportError:
        print("\n[*] Library 'yt-dlp' belum terpasang. Memasang otomatis...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp>=2024.0.0"])
            import yt_dlp
            print("[✓] Library 'yt-dlp' berhasil dipasang!\n")
        except Exception as e:
            print(f"[x] Gagal memasang otomatis: {e}")
            print("    Silakan jalankan: pip install -r requirements.txt")
            return

    outtmpl = str(OUTPUT_DIR / "%(uploader)s" / "%(upload_date)s - %(title)s [%(id)s].%(ext)s")

    ydl_opts = {
        "format": format_spec,
        "outtmpl": outtmpl,
        "merge_output_format": "mp4" if has_ffmpeg else None,
        "download_archive": str(ARCHIVE_FILE),
        "ignoreerrors": True,
        "no_warnings": False,
        "quiet": False,
        "noplaylist": False,
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}] if has_ffmpeg else [],
    }

    if dari_tanggal:
        ydl_opts["dateafter"] = dari_tanggal
    if sampai_tanggal:
        ydl_opts["datebefore"] = sampai_tanggal
    if cookie_file:
        ydl_opts["cookiefile"] = str(cookie_file)

    print("\n[*] Memulai proses pengunduhan channel...")
    print("-" * 65)

    total_channels = len(channels)
    success = 0

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for idx, url in enumerate(channels, start=1):
            print(f"\n[{idx}/{total_channels}] Memproses channel: {url}")
            try:
                ret = ydl.download([url])
                if ret == 0:
                    success += 1
            except Exception as e:
                print(f"[x] Kendala saat mengunduh {url}: {e}")

    print("\n" + "=" * 65)
    print(f"[✓] Selesai! Berhasil memproses {success}/{total_channels} channel.")
    print(f"[✓] Seluruh video tersimpan di folder: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
