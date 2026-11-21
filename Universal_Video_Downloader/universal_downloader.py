# -*- coding: utf-8 -*-
"""
Universal Web Video Downloader (IDM Style)
===========================================
Pengunduh video serbaguna untuk ribuan situs web dan platform streaming.
Mendukung unduhan banyak link (batch), resume, bypass cookie, dan merge kualitas tertinggi (MP4).
"""

import os
import sys
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
TXT_FILE = BASE_DIR / "input_links.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
ARCHIVE_FILE = BASE_DIR / "download_history.txt"
COOKIE_INPUT = BASE_DIR / "input_cookie.txt"
COOKIE_ACTIVE = BASE_DIR / ".cookies_active.txt"


def ensure_templates():
    """Membuat template file jika belum ada."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write(
                "# ==============================================================================\n"
                "# UNIVERSAL VIDEO DOWNLOADER - DAFTAR LINK\n"
                "# Tempelkan (paste) link video web yang ingin diunduh di bawah baris ini.\n"
                "# Satu baris untuk satu link URL.\n"
                "# Contoh:\n"
                "# https://www.youtube.com/watch?v=xxxx\n"
                "# https://vimeo.com/xxxx\n"
                "# https://www.dailymotion.com/video/xxxx\n"
                "# ==============================================================================\n\n"
            )

    if not COOKIE_INPUT.exists():
        with open(COOKIE_INPUT, "w", encoding="utf-8") as f:
            f.write(
                "# ==============================================================================\n"
                "# INPUT COOKIES (OPSIONAL - HANYA JIKA SITUS MEMERLUKAN LOGIN / UMUR 18+)\n"
                "# Ekspor cookies browser dengan ekstensi 'Get cookies.txt LOCALLY' lalu paste di sini.\n"
                "# ==============================================================================\n\n"
            )


def prepare_clean_cookie_file() -> Optional[Path]:
    """Mendeteksi dan menyiapkan cookie jika pengguna mengisi input_cookie.txt."""
    if COOKIE_INPUT.exists() and COOKIE_INPUT.stat().st_size > 20:
        raw_text = COOKIE_INPUT.read_text(encoding="utf-8", errors="ignore").strip()
        lines = [l for l in raw_text.splitlines() if l.strip() and not l.strip().startswith("#")]
        if lines:
            if any("\t" in l for l in lines) or "# netscape" in raw_text.lower():
                idx = raw_text.find("# Netscape")
                clean_content = (raw_text[idx:] if idx != -1 else "# Netscape HTTP Cookie File\n" + raw_text).strip() + "\n"
            else:
                clean_content = "# Netscape HTTP Cookie File\n" + raw_text + "\n"

            COOKIE_ACTIVE.write_text(clean_content, encoding="utf-8")
            return COOKIE_ACTIVE
    return None


def clean_url(url: str) -> str:
    """Membersihkan dan menormalkan URL mirror ke domain utama extractor."""
    cleaned = url.strip().strip("\"' ")
    # Normalisasi mirror domain xhamster (xhsocial, xhwide, xhopen, xhamsterXX) ke domain utama xhamster.com
    # agar extractor bawaan yt-dlp aktif dan tidak terkena 403 Forbidden
    cleaned = re.sub(
        r'https?://(?:www\.)?(?:xhsocial|xhwide|xhopen|xhamster\d+)\.com/',
        'https://xhamster.com/',
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned


def load_links() -> List[str]:
    """Membaca daftar URL dari input_links.txt."""
    ensure_templates()
    links = []
    with open(TXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            raw = line.strip()
            if not raw or raw.startswith("#"):
                continue
            cleaned = clean_url(raw)
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                if cleaned not in links:
                    links.append(cleaned)
    return links


def prompt_links_interactively() -> List[str]:
    """Meminta link langsung jika input_links.txt kosong."""
    print("=" * 65)
    print(" UNIVERSAL WEB VIDEO DOWNLOADER (IDM Style)")
    print("=" * 65)
    print("File 'input_links.txt' masih kosong.")
    print("Pilihan:")
    print("1. Buka Notepad untuk isi banyak link")
    print("2. Ketik / Paste link langsung di terminal\n")

    pilih = input("Pilih (1/2, default 2): ").strip()
    if pilih == "1":
        try:
            os.system(f'notepad.exe "{TXT_FILE}"')
        except Exception:
            pass
        input("\nTekan Enter setelah selesai menyimpan link di Notepad...")
        return load_links()

    print("\nTempelkan link video (tekan Enter 2x jika sudah selesai):")
    entered = []
    while True:
        try:
            line = clean_url(input("> "))
            if not line:
                break
            if line.startswith("http://") or line.startswith("https://"):
                if line not in entered:
                    entered.append(line)
        except (KeyboardInterrupt, EOFError):
            break

    if entered:
        # Simpan juga ke input_links.txt agar tercatat
        with open(TXT_FILE, "a", encoding="utf-8") as f:
            for l in entered:
                f.write(f"{l}\n")

    return entered


def main():
    ensure_templates()
    links = load_links()

    if not links:
        links = prompt_links_interactively()

    if not links:
        print("\n[!] Tidak ada link yang dimasukkan. Program dihentikan.")
        return

    cookie_path = prepare_clean_cookie_file()

    print("\n" + "=" * 65)
    print(" MEMULAI PENGUNDUHAN VIDEO UNIVERSAL")
    print("=" * 65)
    print(f"Total Link     : {len(links)} video")
    print(f"Folder Output  : {OUTPUT_DIR.resolve()}")
    print(f"Cookies Aktif  : {'Ya (' + cookie_path.name + ')' if cookie_path else 'Tidak'}")
    print(f"Merge Kualitas : Kualitas Terbaik (Video + Audio -> MP4)")
    print("=" * 65 + "\n")

    success_count = 0
    fail_count = 0

    for idx, url in enumerate(links, start=1):
        print(f"[{idx}/{len(links)}] Memproses: {url}")

        cmd = [
            "yt-dlp",
            url,
            "--no-warnings",
            "--continue",
            "--no-part",
            "--retries", "3",
            "--fragment-retries", "5",
            "--download-archive", str(ARCHIVE_FILE),
            "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "-f", "bestvideo*+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(OUTPUT_DIR / "%(extractor_key)s" / "%(title)s [%(id)s].%(ext)s"),
        ]

        if cookie_path:
            cmd.extend(["--cookies", str(cookie_path)])

        try:
            res = subprocess.run(cmd)
            if res.returncode == 0:
                print(f"     [✓] Sukses diunduh!\n")
                success_count += 1
            else:
                print(f"     [x] Gagal mengunduh (kode keluar: {res.returncode})\n")
                fail_count += 1
        except KeyboardInterrupt:
            print("\n[!] Dihentikan oleh pengguna (Ctrl+C).")
            break
        except Exception as e:
            print(f"     [!] Terjadi kesalahan sistem: {e}\n")
            fail_count += 1

    print("=" * 65)
    print(" RINGKASAN UNDUHAN")
    print("=" * 65)
    print(f"- Total Link : {len(links)}")
    print(f"- Berhasil   : {success_count}")
    print(f"- Gagal      : {fail_count}")
    print(f"- File Video : {OUTPUT_DIR.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    main()
