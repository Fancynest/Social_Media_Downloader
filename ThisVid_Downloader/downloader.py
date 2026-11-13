# -*- coding: utf-8 -*-
import os
import sys
import re
import json
import socket
import urllib.request
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# =====================================================================
# DNS-OVER-HTTPS (DoH) RESOLVER
# Mencegah pembajakan DNS oleh provider (ICONNET / Internet Sehat)
# Menembus DNS Poisoning secara langsung tanpa perlu VPN!
# =====================================================================
_orig_getaddrinfo = socket.getaddrinfo
_dns_cache = {}

def doh_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    if isinstance(host, str) and ("thisvid.com" in host or "magsrv.com" in host):
        if host not in _dns_cache:
            try:
                url = f"https://cloudflare-dns.com/dns-query?name={host}&type=A"
                req = urllib.request.Request(
                    url,
                    headers={
                        "Accept": "application/dns-json",
                        "User-Agent": "Mozilla/5.0"
                    }
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    res = json.loads(r.read().decode())
                    for ans in res.get("Answer", []):
                        if ans.get("type") == 1 and ans.get("data"):
                            _dns_cache[host] = ans.get("data")
                            break
            except Exception:
                pass
        if host in _dns_cache:
            return _orig_getaddrinfo(_dns_cache[host], port, family, type, proto, flags)
    return _orig_getaddrinfo(host, port, family, type, proto, flags)

socket.getaddrinfo = doh_getaddrinfo

# Import yt_dlp setelah socket dipatch
import yt_dlp

BASE_DIR = Path(__file__).resolve().parent
TXT_FILE = BASE_DIR / "link_video.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
ARCHIVE_FILE = BASE_DIR / "download_history.txt"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
PROXY_FILE = BASE_DIR / "input_proxy.txt"


def clean_url(raw_url: str) -> str:
    url = raw_url.strip()
    if "?" in url and "thisvid.com" in url:
        url = url.split("?")[0]
    return url


def load_links():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write("# Tempelkan link video ThisVid di sini (1 per baris):\n")
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


def get_proxy() -> str | None:
    if PROXY_FILE.exists():
        try:
            content = PROXY_FILE.read_text(encoding="utf-8", errors="ignore").strip()
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    return line
        except Exception:
            pass
    return os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY") or None


def download_single_video(url: str, proxy: str | None = None) -> bool:
    output_template = str(OUTPUT_DIR / "%(uploader,creator)s_%(id)s_%(title).60s.%(ext)s")
    
    ydl_opts = {
        'outtmpl': output_template,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'merge_output_format': 'mp4',
        'windowsfilenames': True,
        'nocheckcertificate': True,
        'http_chunk_size': 10485760,  # 10MB chunk refresh untuk cegah TCP throttling
        'ignoreerrors': False,
        'no_warnings': True,
        'download_archive': str(ARCHIVE_FILE),
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Referer': 'https://thisvid.com/'
        }
    }

    clean_cookie = prepare_clean_cookie_file()
    if clean_cookie and clean_cookie.exists():
        ydl_opts['cookiefile'] = str(clean_cookie)

    if proxy:
        ydl_opts['proxy'] = proxy

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            retcode = ydl.download([url])
            return retcode == 0
    except Exception as e:
        print(f"  [x] Error: {e}")
        return False


def run_download():
    print("=" * 65)
    print("           THISVID MASS VIDEO DOWNLOADER (FULL SPEED)")
    print("=" * 65)
    print("[*] Anti-Sensor DoH : AKTIF (Bypass otomatis pembajakan DNS ISP)")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    has_cookie = COOKIE_FILE.exists() and COOKIE_FILE.stat().st_size > 10
    if has_cookie:
        print("[+] Cookies aktif   : 'input_cookie.txt' dimuat (Akses video login/member)")
    else:
        print("[i] Mode Akun       : Tamu (Tanpa cookies)")

    proxy = get_proxy()
    if proxy:
        print(f"[+] Proxy aktif     : {proxy}")

    links = load_links()
    if not links:
        print(f"\n[!] '{TXT_FILE.name}' masih kosong atau belum ada link valid.")
        print("[*] Membuka Notepad untuk mengisi link...")
        try:
            os.system(f'notepad.exe "{TXT_FILE}"')
        except Exception:
            pass
        input("\nTekan Enter setelah selesai mengisi tautan & menyimpan file...")
        links = load_links()
        if not links:
            print("[!] Tidak ada tautan untuk diproses.")
            return

    print(f"\n Folder Simpan : {OUTPUT_DIR}")
    print(f" Total Tautan  : {len(links)}\n")

    success_count, fail_count = 0, 0

    for idx, url in enumerate(links, 1):
        print("-" * 65)
        print(f"[{idx}/{len(links)}] Memproses: {url}")
        
        ok = download_single_video(url, proxy=proxy)

        if ok:
            print("  [✓] Sukses diunduh.")
            success_count += 1
        else:
            print("  [x] Gagal atau video tidak dapat diakses.")
            fail_count += 1

    print("\n" + "=" * 65)
    print("                    RINGKASAN PENGUNDUHAN")
    print("=" * 65)
    print(f" Total Diproses : {len(links)}")
    print(f" Berhasil       : {success_count}")
    print(f" Gagal          : {fail_count}")
    print(f" Folder Simpan  : {OUTPUT_DIR}")
    print("=" * 65)

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
