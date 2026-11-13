# -*- coding: utf-8 -*-
"""
YouTube Batch Downloader (Video, Shorts, Playlist)
==================================================
Mengunduh video, shorts, dan playlist YouTube dari daftar link Notepad
dengan kualitas video & audio maksimal serta dukungan bypass cookies 18+.
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
TXT_FILE = BASE_DIR / "link_youtube.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
ARCHIVE_FILE = BASE_DIR / "download_history.txt"
COOKIE_INPUT = BASE_DIR / "input_cookie.txt"
COOKIE_ACTIVE = BASE_DIR / ".cookies_active.txt"
COOKIE_DIRECT = BASE_DIR / "cookies.txt"


def prepare_clean_cookie_file() -> Path | None:
    # 1. Cek apakah ada input_cookie.txt di folder saat ini atau parent
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

    # 2. Cek apakah ada cookies.txt langsung
    for c_dir in [COOKIE_DIRECT, BASE_DIR.parent / "cookies.txt"]:
        if c_dir.exists() and c_dir.stat().st_size > 20:
            return c_dir

    return None


def clean_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("@"):
        return f"https://www.youtube.com/{url}"
    return url


def load_links():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write("# Tempelkan tautan video YouTube di sini (1 per baris):\n")
        return []

    links = []
    with open(TXT_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            links.append(clean_url(line))
    return links


def main():
    print("=" * 65)
    print("        YOUTUBE BATCH DOWNLOADER (VIDEO, SHORTS, PLAYLIST)")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    links = load_links()

    if not links:
        print(f"\n[!] Berkas '{TXT_FILE.name}' masih kosong.")
        print(f"    Silakan buka '{TXT_FILE.name}' atau klik 'BUKA_NOTEPAD_LINK.bat'")
        print("    lalu tempelkan tautan video YouTube yang ingin diunduh.")
        return

    print(f"[*] Ditemukan {len(links)} tautan dalam antrean.")

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
        print("[!] FFmpeg tidak terdeteksi di sistem PATH. Mengunduh format gabungan tunggal.")

    try:
        import yt_dlp
    except ImportError:
        print("\n[x] Library 'yt-dlp' belum terpasang.")
        print("    Jalankan perintah: pip install yt-dlp")
        return

    outtmpl = str(OUTPUT_DIR / "%(title)s [%(id)s].%(ext)s")

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

    if cookie_file:
        ydl_opts["cookiefile"] = str(cookie_file)

    print("\n[*] Memulai proses pengunduhan...")
    print("-" * 65)

    total = len(links)
    success = 0

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for idx, url in enumerate(links, start=1):
            print(f"\n[{idx}/{total}] Memproses: {url}")
            try:
                ret = ydl.download([url])
                if ret == 0:
                    success += 1
            except Exception as e:
                print(f"[x] Kendala saat mengunduh {url}: {e}")

    print("\n" + "=" * 65)
    print(f"[✓] Pengunduhan selesai! Berhasil diproses: {success}/{total}")
    print(f"[✓] Berkas tersimpan di folder: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
