# -*- coding: utf-8 -*-
import os
import sys
import re
import time
import json
import shutil
import urllib.request
import subprocess
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


def find_ytdlp() -> str:
    bin_path = shutil.which("yt-dlp")
    if bin_path:
        return bin_path
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for match in winget_path.glob("**/yt-dlp.exe"):
        if match.is_file():
            return str(match)
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
    with open(ARCHIVE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        return set(line.strip() for line in f if line.strip())


def add_to_archive(item_id: str):
    with open(ARCHIVE_FILE, "a", encoding="utf-8") as f:
        f.write(f"{item_id}\n")


def load_links():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write("# Tempelkan tautan video atau foto di sini (1 per baris):\n")
        return []

    links = []
    with open(TXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue
            cleaned = clean_url(line)
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                links.append(cleaned)
    return links


def download_file_direct(url: str, dest: Path, label: str = "Media") -> bool:
    temp_path = dest.with_suffix(".tmp")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    )
    try:
        with urllib.request.urlopen(req, timeout=45) as resp, open(temp_path, "wb") as f:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            t0 = time.time()
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                downloaded += len(chunk)
                pct = (downloaded / total * 100) if total else 0
                speed = (downloaded / (time.time() - t0 + 0.001)) / (1024 * 1024)
                if total:
                    sys.stdout.write(f"\r  [{label}] {pct:5.1f}% ({downloaded/(1024*1024):.1f}/{total/(1024*1024):.1f} MB) - {speed:.2f} MB/s")
                else:
                    sys.stdout.write(f"\r  [{label}] {downloaded/(1024*1024):.1f} MB - {speed:.2f} MB/s")
                sys.stdout.flush()
        print()
        if dest.exists():
            dest.unlink()
        temp_path.rename(dest)
        return True
    except Exception as e:
        print(f"\n  [x] Gagal mengunduh: {e}")
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        return False


def try_download_twitter_api(url: str, archive_set: set) -> bool:
    match = re.search(r'(?:x|twitter)\.com/(?:#!/)?(\w+)/status/(\d+)', url)
    if not match:
        return False

    username, tweet_id = match.groups()
    archive_key = f"twitter_{tweet_id}"

    if archive_key in archive_set:
        if any(tweet_id in f.name for f in OUTPUT_DIR.glob(f"*{tweet_id}*")):
            print(f"  [i] Media ({tweet_id}) sudah ada dalam riwayat, dilewati.")
            return True

    api_endpoints = [
        f"https://api.fxtwitter.com/{username}/status/{tweet_id}",
        f"https://api.vxtwitter.com/{username}/status/{tweet_id}"
    ]

    for api_url in api_endpoints:
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))

            tweet = data.get("tweet", {})
            media = tweet.get("media", {})
            videos = media.get("videos", [])
            photos = media.get("photos", [])

            if not videos and not photos:
                all_m = media.get("all", [])
                videos = [m for m in all_m if m.get("type") in ("video", "gif")]
                photos = [m for m in all_m if m.get("type") == "photo"]

            total_items = len(videos) + len(photos)
            if total_items == 0:
                continue

            raw_title = tweet.get("text", "") or "media"
            clean_title = sanitize_filename(raw_title)
            success_download = True
            idx = 1

            for vid in videos:
                suffix = f"_{idx}" if total_items > 1 else ""
                dest = OUTPUT_DIR / f"{username}_{tweet_id}{suffix}_{clean_title}.mp4"
                variants = vid.get("variants", [])
                mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
                best_url = max(mp4s, key=lambda x: x.get("bitrate", 0))["url"] if mp4s else vid.get("url")
                if not best_url:
                    continue
                print(f"  [+] Mengunduh video (kualitas maksimal)...")
                if not download_file_direct(best_url, dest, label="Video"):
                    success_download = False
                idx += 1

            for pic in photos:
                pic_url = pic.get("url", "")
                if not pic_url:
                    continue
                ext = "png" if ".png" in pic_url.lower() else ("webp" if ".webp" in pic_url.lower() else "jpg")
                orig_url = f"{pic_url.split('?')[0]}?name=orig" if "pbs.twimg.com" in pic_url else pic_url
                suffix = f"_{idx}" if total_items > 1 else ""
                dest = OUTPUT_DIR / f"{username}_{tweet_id}{suffix}_{clean_title}.{ext}"
                print(f"  [+] Mengunduh foto ({ext.upper()} resolusi asli)...")
                if not download_file_direct(orig_url, dest, label="Foto"):
                    if not download_file_direct(pic_url, dest, label="Foto"):
                        success_download = False
                idx += 1

            if success_download and idx > 1:
                add_to_archive(archive_key)
                archive_set.add(archive_key)
                print(f"  [✓] Sukses disimpan ({total_items} media).")
                return True
        except Exception:
            continue

    return False


def prepare_clean_cookie_file() -> Path | None:
    if not COOKIE_FILE.exists() or COOKIE_FILE.stat().st_size < 10:
        return None
    try:
        text = COOKIE_FILE.read_text(encoding="utf-8", errors="ignore")
        idx = text.find("# Netscape")
        if idx != -1:
            clean_content = text[idx:].strip() + "\n"
        else:
            clean_content = "# Netscape HTTP Cookie File\n" + text.strip() + "\n"

        clean_path = BASE_DIR / ".cookies_active.txt"
        clean_path.write_text(clean_content, encoding="utf-8")
        return clean_path
    except Exception:
        return COOKIE_FILE if COOKIE_FILE.exists() else None


def try_download_ytdlp(url: str) -> bool:
    ytdlp_bin = find_ytdlp()
    output_template = str(OUTPUT_DIR / "%(uploader)s_%(id)s_%(title).50s.%(ext)s")
    cmd = [
        ytdlp_bin,
        "--no-warnings",
        "--ignore-errors",
        "--no-overwrites",
        "--continue",
        "--windows-filenames",
        "--download-archive", str(ARCHIVE_FILE),
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", output_template,
    ]

    clean_cookie = prepare_clean_cookie_file()
    if clean_cookie and clean_cookie.exists():
        cmd.extend(["--cookies", str(clean_cookie)])

    cmd.append(url)
    try:
        res = subprocess.run(cmd)
        return res.returncode == 0
    except Exception as e:
        print(f"  [x] Error yt-dlp: {e}")
        return False


def run_download():
    print("=" * 60)
    print(" MASS MEDIA DOWNLOADER (X / TWITTER & ALL SITES)")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    archive_set = load_archive()

    has_cookie = COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 10
    if has_cookie:
        print("[+] Cookies aktif: 'input_cookie.txt' dimuat (Bypass konten sensitif & 18+)")
    else:
        print("[i] Berjalan dalam Mode Tamu (Tanpa cookies)")
        print("    Tips: Jika ada konten sensitif/18+ yang gagal diunduh, ekspor cookies")
        print("    dari x.com ke berkas 'input_cookie.txt' (klik BUKA_NOTEPAD_COOKIE.bat).")

    links = load_links()
    if not links:
        print(f"[!] '{TXT_FILE.name}' masih kosong atau belum ada link valid.")
        print("[*] Silakan isi tautan ke berkas tersebut lalu simpan (Ctrl+S).")
        try:
            os.system(f'notepad.exe "{TXT_FILE}"')
        except Exception:
            pass
        input("\nTekan Enter setelah selesai mengisi tautan...")
        links = load_links()
        if not links:
            print("[!] Tidak ada tautan untuk diproses.")
            return

    print(f" Folder Simpan : {OUTPUT_DIR}")
    print(f" Total Tautan  : {len(links)}\n")

    success_count, fail_count = 0, 0

    for idx, url in enumerate(links, 1):
        print("-" * 60)
        print(f"[{idx}/{len(links)}] Memproses: {url}")
        is_twitter = ("x.com" in url) or ("twitter.com" in url)
        downloaded = False

        if is_twitter:
            downloaded = try_download_twitter_api(url, archive_set)

        if not downloaded:
            print("  [*] Mencoba unduh via yt-dlp engine...")
            downloaded = try_download_ytdlp(url)

        if downloaded:
            success_count += 1
        else:
            print("  [x] Gagal mengunduh media.")
            fail_count += 1

    print("\n" + "=" * 60)
    print(" RINGKASAN PENGUNDUHAN")
    print("=" * 60)
    print(f" Total Diproses : {len(links)}")
    print(f" Berhasil       : {success_count}")
    print(f" Gagal          : {fail_count}")
    print(f" Folder Simpan  : {OUTPUT_DIR}")
    print("=" * 60)

    try:
        os.system(f'explorer.exe "{OUTPUT_DIR}"')
    except Exception:
        pass


if __name__ == "__main__":
    try:
        run_download()
    except KeyboardInterrupt:
        print("\n[!] Dihentikan oleh pengguna.")
    input("\nTekan Enter untuk keluar...")
