# -*- coding: utf-8 -*-
"""
Twitter / X Batch Downloader (Foto & Video)
===========================================
Mengunduh foto resolusi asli dan video resolusi tertinggi dari daftar tautan
postingan X/Twitter menggunakan Fast Direct CDN Resolver & yt-dlp fallback.
"""

import os
import sys
import re
import time
import json
import shutil
import urllib.request
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
TXT_FILE = BASE_DIR / "link_video.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
ARCHIVE_FILE = BASE_DIR / "download_history.txt"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
COOKIE_ACTIVE = BASE_DIR / ".cookies_active.txt"


def find_ytdlp() -> str:
    bin_path = shutil.which("yt-dlp")
    if bin_path:
        return bin_path
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for match in winget_path.glob("**/yt-dlp.exe"):
        if match.is_file():
            return str(match)
    try:
        import yt_dlp
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp>=2024.0.0"])
        except Exception:
            pass
    return "yt-dlp"


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[\r\n\t]+', ' ', name)
    name = re.sub(r'[\\/*?:"<>|]', '_', name)
    name = re.sub(r'[\x00-\x1f\x7f]', '', name).strip(' ._')
    return name[:60] if name else "media"


def clean_url(raw_url: str) -> str:
    url = raw_url.strip()
    url = re.sub(r'https?://(?:www\.)?(?:vx|fx)?twitter\.com', 'https://x.com', url)
    url = re.sub(r'https?://(?:www\.)?fixupx\.com', 'https://x.com', url)
    if "status/" in url and "?" in url:
        url = url.split("?")[0]
    return url


def load_archive() -> set:
    if not ARCHIVE_FILE.exists():
        return set()
    try:
        with open(ARCHIVE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            return set(line.strip() for line in f if line.strip())
    except Exception:
        return set()


def append_archive(identifier: str):
    try:
        with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
            f.write(f"{identifier}\n")
    except Exception:
        pass


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


def download_file(url: str, dest_path: Path) -> bool:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://x.com/",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response, open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)
        return True
    except Exception as e:
        print(f"     [!] Kendala unduh langsung: {e}")
        if dest_path.exists():
            try:
                dest_path.unlink()
            except Exception:
                pass
        return False


def try_download_twitter_api(url: str) -> bool:
    match = re.search(r'x\.com/([^/]+)/status/(\d+)', url)
    if not match:
        return False

    author, tweet_id = match.group(1), match.group(2)
    api_url = f"https://api.vxtwitter.com/{author}/status/{tweet_id}"
    req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            data = json.loads(res.read().decode("utf-8"))
    except Exception:
        return False

    date_str = ""
    if "date" in data and data["date"]:
        try:
            dt = parsedate_to_datetime(data["date"])
            date_str = dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    caption_clean = sanitize_filename(data.get("text", "tweet"))
    base_prefix = f"[{date_str}] [{author}] {caption_clean} ({tweet_id})"

    media_list = data.get("media_extended", [])
    if not media_list and "mediaURLs" in data:
        media_list = [{"url": u, "type": "image"} for u in data["mediaURLs"]]

    if not media_list:
        return False

    success_any = False
    for i, m in enumerate(media_list):
        m_type = m.get("type", "image")
        m_url = m.get("url", "")
        if not m_url:
            continue

        suffix = f"_{i+1}" if len(media_list) > 1 else ""

        if m_type in ("video", "gif"):
            filename = f"{base_prefix}{suffix}.mp4"
            dest = OUTPUT_DIR / filename
            if dest.exists() and dest.stat().st_size > 1000:
                print(f"     [✓] Video sudah ada: {filename}")
                success_any = True
                continue
            print(f"     [*] Mengunduh Video via CDN...")
            if download_file(m_url, dest):
                print(f"     [✓] Video tersimpan: {filename}")
                success_any = True
        else:
            orig_url = m_url.split("?")[0] + "?name=orig" if "twimg.com" in m_url else m_url
            ext = "jpg"
            if ".png" in m_url.lower():
                ext = "png"
            elif ".webp" in m_url.lower():
                ext = "webp"

            filename = f"{base_prefix}{suffix}.{ext}"
            dest = OUTPUT_DIR / filename
            if dest.exists() and dest.stat().st_size > 1000:
                print(f"     [✓] Foto sudah ada: {filename}")
                success_any = True
                continue
            print(f"     [*] Mengunduh Foto resolusi asli...")
            if download_file(orig_url, dest) or download_file(m_url, dest):
                print(f"     [✓] Foto tersimpan: {filename}")
                success_any = True

    return success_any


def download_with_ytdlp(url: str, ytdlp_bin: str, cookie_file: Path | None) -> bool:
    outtmpl = str(OUTPUT_DIR / "[%(upload_date)s] [%(uploader)s] %(title).60s (%(id)s).%(ext)s")
    cmd = [
        ytdlp_bin,
        "--no-playlist",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", outtmpl,
        "--no-warnings",
        url,
    ]
    if cookie_file:
        cmd.extend(["--cookies", str(cookie_file)])

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    if res.returncode == 0:
        print("     [✓] Berhasil diunduh via yt-dlp!")
        return True
    return False


def load_links():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write("# Tempelkan tautan postingan X / Twitter di sini (1 per baris):\n")
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
    print("      TWITTER / X BATCH DOWNLOADER (FOTO & VIDEO)")
    print("=" * 65)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ytdlp_bin = find_ytdlp()
    cookie_file = prepare_clean_cookie_file()
    archive = load_archive()

    if cookie_file:
        print(f"[*] Menggunakan file cookies: {cookie_file.name}")
    else:
        print("[*] Berjalan dalam mode publik anonim (tanpa cookies).")

    links = load_links()
    if not links:
        print(f"\n[!] Berkas '{TXT_FILE.name}' masih kosong.")
        print(f"    Silakan buka '{TXT_FILE.name}' atau klik 'BUKA_NOTEPAD_LINK.bat'")
        print("    lalu tempelkan tautan postingan yang ingin diunduh.")
        return

    print(f"[*] Ditemukan {len(links)} tautan dalam antrean.")
    print("-" * 65)

    success_count = 0
    total = len(links)

    for idx, url in enumerate(links, start=1):
        print(f"\n[{idx}/{total}] Memproses: {url}")
        m = re.search(r'status/(\d+)', url)
        tweet_id = m.group(1) if m else url

        if tweet_id in archive:
            print("     [-] Sudah pernah diunduh sebelumnya, dilewati.")
            success_count += 1
            continue

        ok = try_download_twitter_api(url)
        if not ok:
            print("     [*] Direct resolver gagal/konten sensitif. Mencoba yt-dlp...")
            ok = download_with_ytdlp(url, ytdlp_bin, cookie_file)

        if ok:
            append_archive(tweet_id)
            archive.add(tweet_id)
            success_count += 1
        else:
            print(f"     [x] Gagal mengunduh postingan: {url}")

    print("\n" + "=" * 65)
    print(f"[✓] Selesai! Berhasil mengunduh: {success_count}/{total} postingan.")
    print(f"[✓] Seluruh berkas tersimpan di: {OUTPUT_DIR}")
    print("=" * 65)


if __name__ == "__main__":
    main()
