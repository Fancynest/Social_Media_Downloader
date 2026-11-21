"""
TeraBox Master Downloader
Mengunduh file video, foto, dan dokumen dari TeraBox dengan kualitas asli (Master Original/Lossless),
menggunakan curl_cffi Chrome impersonation untuk bypass Cloudflare/verifikasi bot,
dan akselerasi unduhan 16 thread (aria2c multi-connection).
"""

import os
import sys
import re
import json
import time
import shutil
import subprocess
from urllib.parse import urlparse, parse_qs, unquote
from datetime import datetime

try:
    from curl_cffi import requests
except ImportError:
    import requests

# Konfigurasi Direktori
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_DIR = os.path.join(BASE_DIR, "Hasil_Download")
LINKS_FILE = os.path.join(BASE_DIR, "input_links.txt")
COOKIE_FILE = os.path.join(BASE_DIR, "input_cookie.txt")
HISTORY_FILE = os.path.join(BASE_DIR, "download_history.txt")

os.makedirs(DOWNLOAD_DIR, exist_ok=True)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

def format_size(bytes_size):
    """Konversi ukuran byte ke format B, KB, MB, GB yang mudah dibaca."""
    try:
        n = float(bytes_size)
    except (ValueError, TypeError):
        return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024.0:
            return f"{n:.2f} {unit}"
        n /= 1024.0
    return f"{n:.2f} PB"

def clean_filename(filename):
    """Membersihkan karakter ilegal pada nama file untuk Windows."""
    return re.sub(r'[\\/*?:"<>|]', '_', filename).strip()

def load_history():
    """Membaca riwayat unduhan."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    history = set()
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parts = line.strip().split(" | ")
                if parts:
                    history.add(parts[0].strip())
    except Exception:
        pass
    return history

def save_history(file_name, file_size, source_url):
    """Menyimpan file yang berhasil diunduh ke riwayat."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    size_str = format_size(file_size)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{file_name} | {size_str} | {source_url} | {now}\n")

def parse_cookies():
    """Membaca dan mem-parsing cookie dari input_cookie.txt."""
    cookies = {}
    if not os.path.exists(COOKIE_FILE):
        return cookies

    try:
        with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format Netscape HTTP Cookie File
            if "\t" in line:
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies[parts[5].strip()] = parts[6].strip()
            # Format Name=Value (bisa satu baris banyak cookie dipisah titik-koma)
            elif "=" in line:
                pairs = line.split(";")
                for pair in pairs:
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        if k.strip():
                            cookies[k.strip()] = v.strip()
    except Exception as e:
        print(f" [!] Peringatan membaca cookie: {e}")

    return cookies

def extract_surl_and_pwd(url):
    """Mengekstrak shorturl (surl) dan password (pwd) dari berbagai format link TeraBox."""
    url = url.strip()
    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    pwd = query.get("pwd", [None])[0]
    surl = query.get("surl", [None])[0]

    if not surl:
        # Cek pola path seperti /s/1ABCDEF atau /s/ABCDEF
        match = re.search(r'/s/(?:1)?([a-zA-Z0-9_\-]+)', parsed.path)
        if match:
            surl = match.group(1)
        else:
            # Fallback ambil bagian akhir path
            parts = [p for p in parsed.path.split('/') if p]
            if parts:
                last_part = parts[-1]
                if last_part.startswith("1"):
                    surl = last_part[1:]
                else:
                    surl = last_part

    return surl, pwd

def create_session(cookies_dict):
    """Membuat HTTP Session dengan TLS Fingerprint Chrome untuk bypass Cloudflare."""
    try:
        session = requests.Session(impersonate="chrome120")
    except Exception:
        import requests as std_requests
        session = std_requests.Session()

    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.terabox.app/",
    })

    if cookies_dict:
        session.cookies.update(cookies_dict)

    return session

def fetch_terabox_file_list(session, raw_url, surl, pwd=None):
    """
    Menghubungi TeraBox untuk mendapatkan metadata file asli dan tautan dlink.
    Mendukung bypass jsToken dinamis dan verifikasi password (pwd).
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": raw_url,
        "Accept": "application/json, text/plain, */*",
    }

    # 1. Kunjungi halaman awal untuk memicu cookies & mengekstrak jsToken
    landing_url = f"https://www.terabox.app/sharing/link?surl={surl}"
    try:
        r_page = session.get(landing_url, headers=headers, timeout=20)
    except Exception as e:
        print(f"     [!] Gagal mengakses halaman TeraBox: {e}")
        return None

    # Ekstrak jsToken dari HTML
    js_token = None
    js_match = re.search(r'fn%28%22([a-fA-F0-9]+)%22%29', r_page.text)
    if js_match:
        js_token = js_match.group(1)
    else:
        js_match2 = re.search(r'fn\("([a-fA-F0-9]+)"\)', r_page.text)
        if js_match2:
            js_token = js_match2.group(1)
        else:
            js_match3 = re.search(r'jsToken\s*[:=]\s*["\']([a-fA-F0-9]+)["\']', r_page.text)
            if js_match3:
                js_token = js_match3.group(1)

    # Ekstrak dp-logid jika ada
    logid = None
    log_match = re.search(r'dp-logid=([^&"\'\s;]+)', r_page.text)
    if log_match:
        logid = log_match.group(1)

    # 2. Verifikasi Password jika link diproteksi sandi
    if pwd:
        verify_url = "https://www.terabox.app/share/verify"
        post_data = {
            "pwd": pwd,
            "surl": surl,
        }
        try:
            r_verify = session.post(verify_url, data=post_data, headers=headers, timeout=15)
            v_data = r_verify.json()
            if v_data.get("errno") != 0:
                print(f"     [!] Verifikasi kata sandi gagal (errno: {v_data.get('errno')})")
        except Exception:
            pass

    # 3. Request API file list (mencoba shorturl murni dan dengan awalan 1 jika perlu)
    candidates_surl = [surl]
    if not surl.startswith("1"):
        candidates_surl.append("1" + surl)
    else:
        candidates_surl.append(surl[1:])

    for cand in candidates_surl:
        params = {
            "app_id": "250528",
            "web": "1",
            "channel": "0",
            "shorturl": cand,
            "root": "1",
        }
        if js_token:
            params["jsToken"] = js_token
        if logid:
            params["dp-logid"] = logid

        api_domains = ["www.terabox.app", "www.1024tera.com", "teraboxapp.com"]
        for domain in api_domains:
            api_url = f"https://{domain}/share/list"
            try:
                res = session.get(api_url, params=params, headers=headers, timeout=20)
                if res.status_code == 200:
                    data = res.json()
                    errno = data.get("errno")
                    if errno == 0 and "list" in data and len(data["list"]) > 0:
                        return data["list"]
                    elif errno == -1 and not pwd:
                        print("     [!] Link ini membutuhkan Password / Kata Sandi!")
                        return "NEED_PASSWORD"
            except Exception:
                continue

    return None

def download_with_aria2c(dlink, file_path, cookies_dict):
    """
    Mengunduh file master menggunakan aria2c dengan 16 parallel fragment connection.
    Mendukung resume dan throughput maksimal.
    """
    aria2_path = shutil.which("aria2c")
    if not aria2_path:
        return False

    out_dir = os.path.dirname(file_path)
    out_name = os.path.basename(file_path)

    cmd = [
        aria2_path,
        "-c",                       # Lanjutkan unduhan sebagian jika ada
        "-x", "16",                 # 16 koneksi per server
        "-s", "16",                 # 16 fragmentasi simultan
        "-k", "1M",                 # Ukuran fragment minimum 1MB
        "--max-connection-per-server=16",
        "--min-split-size=1M",
        "--summary-interval=1",
        f"--dir={out_dir}",
        f"--out={out_name}",
        f"--header=User-Agent: {USER_AGENT}",
        "--header=Referer: https://www.terabox.app/",
    ]

    # Pasang Cookie ke aria2c
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies_dict.items()])
    if cookie_str:
        cmd.append(f"--header=Cookie: {cookie_str}")

    cmd.append(dlink)

    try:
        res = subprocess.run(cmd)
        return res.returncode == 0
    except Exception as e:
        print(f"     [!] Error saat menjalankan aria2c: {e}")
        return False

def download_with_python_stream(session, dlink, file_path, total_size=0):
    """
    Fallback pengunduh streaming Python jika aria2c tidak tersedia.
    Mendukung chunked transfer, resume Range, dan progress bar interaktif.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.terabox.app/",
    }

    downloaded = 0
    mode = "wb"
    if os.path.exists(file_path):
        downloaded = os.path.getsize(file_path)
        if total_size and downloaded >= total_size:
            return True
        headers["Range"] = f"bytes={downloaded}-"
        mode = "ab"

    try:
        with session.get(dlink, headers=headers, stream=True, timeout=30) as r:
            if r.status_code not in [200, 206]:
                print(f"     [x] Server merespon kode: {r.status_code}")
                return False

            content_len = r.headers.get('content-length')
            if content_len:
                total_size = downloaded + int(content_len)

            start_time = time.time()
            last_print = 0
            with open(file_path, mode) as f:
                for chunk in r.iter_content(chunk_size=1024 * 1024):  # 1MB buffer
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        now = time.time()
                        if now - last_print > 0.5:
                            last_print = now
                            elapsed = now - start_time if (now - start_time) > 0 else 0.001
                            speed = (downloaded - (downloaded if mode == 'wb' else 0)) / elapsed
                            pct = (downloaded / total_size * 100) if total_size else 0
                            bar = ('#' * int(pct // 5)).ljust(20, '-')
                            sys.stdout.write(
                                f"\r     [{bar}] {pct:.1f}% ({format_size(downloaded)} / {format_size(total_size)}) @ {format_size(speed)}/s"
                            )
                            sys.stdout.flush()

            sys.stdout.write("\n")
            return True
    except Exception as e:
        print(f"\n     [x] Gagal saat mengunduh via streaming: {e}")
        return False

def process_single_link(session, raw_url, cookies_dict, history):
    """Memproses satu tautan TeraBox: resolving -> direct dlink -> multi-thread download."""
    raw_url = raw_url.strip()
    if not raw_url or raw_url.startswith("#"):
        return False

    surl, pwd = extract_surl_and_pwd(raw_url)
    if not surl:
        print(f"     [x] Gagal mengenali ID share TeraBox dari: {raw_url}")
        return False

    print(f"     [*] Menyelesaikan metadata TeraBox (ID: {surl}) ...")
    file_items = fetch_terabox_file_list(session, raw_url, surl, pwd)

    if file_items == "NEED_PASSWORD":
        user_pwd = input("     [?] Tautan ini butuh kata sandi. Masukkan password (4 digit): ").strip()
        if user_pwd:
            file_items = fetch_terabox_file_list(session, raw_url, surl, user_pwd)

    if not file_items or isinstance(file_items, str):
        print("     [x] Gagal mengambil daftar file TeraBox.")
        print("         Petunjuk: Jika file berukuran besar (>500MB), pastikan cookie 'ndus' sudah diisi di 'input_cookie.txt'.")
        return False

    total_files = len(file_items)
    print(f"     [✓] Ditemukan {total_files} file dalam share link ini.")

    success_count = 0
    for idx, item in enumerate(file_items, 1):
        filename = clean_filename(item.get("server_filename", f"terabox_file_{int(time.time())}"))
        filesize = item.get("size", 0)
        dlink = item.get("dlink")

        print(f"\n     [{idx}/{total_files}] File: {filename}")
        print(f"          Ukuran : {format_size(filesize)}")
        print(f"          Kualitas: Master Original (Lossless Bit-for-Bit)")

        if not dlink:
            print("          [x] Direct download link (dlink) tidak tersedia untuk file ini.")
            continue

        target_path = os.path.join(DOWNLOAD_DIR, filename)

        # Cek apakah file sudah pernah diunduh lengkap
        if os.path.exists(target_path) and os.path.getsize(target_path) >= filesize and filesize > 0:
            print("          [i] File sudah ada dan lengkap di folder Hasil_Download (Dilewati).")
            success_count += 1
            continue

        print("          [*] Memulai unduhan super cepat (16 Threads) ...")
        # 1. Coba unduh dengan aria2c (16 threads paralel)
        success = download_with_aria2c(dlink, target_path, cookies_dict)

        # 2. Fallback ke streaming Python jika aria2c gagal atau tidak ada
        if not success:
            print("          [*] Beralih ke pengunduh bawaan (Python chunked streaming) ...")
            success = download_with_python_stream(session, dlink, target_path, filesize)

        if success:
            print(f"          [✓] Berhasil diunduh: {filename}")
            save_history(filename, filesize, raw_url)
            success_count += 1
        else:
            print(f"          [x] Gagal mengunduh: {filename}")

    return success_count > 0

def main():
    print("=" * 65)
    print("   TERABOX MASTER ORIGINAL DOWNLOADER (16 THREADS ACCELERATED)   ")
    print("   Format   : Video, Foto, Dokumen Full Original Bit-for-Bit     ")
    print("   Engine   : curl_cffi Chrome Impersonation + aria2c 16-Thread  ")
    print("=" * 65)

    cookies_dict = parse_cookies()
    if cookies_dict:
        print(f"[*] Cookie terdeteksi ({len(cookies_dict)} parameter termuat).")
    else:
        print("[!] Tidak ada cookie terdeteksi di input_cookie.txt.")
        print("    (Untuk file besar >500MB disarankan mengisi cookie 'ndus' dari browser).")

    session = create_session(cookies_dict)
    history = load_history()

    # Membaca daftar tautan
    links = []
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("#"):
                    links.append(l)

    if not links:
        print(f"\n[!] Berkas '{os.path.basename(LINKS_FILE)}' kosong atau belum diisi.")
        user_url = input("Masukkan tautan TeraBox (atau tekan Enter untuk keluar): ").strip()
        if user_url:
            links.append(user_url)
        else:
            print("[*] Selesai. Tidak ada tautan yang diproses.")
            return

    print(f"\n[*] Total {len(links)} tautan TeraBox siap diunduh.")
    print(f"[*] Lokasi penyimpanan: {DOWNLOAD_DIR}\n")

    successful_links = 0
    for idx, link in enumerate(links, 1):
        print(f"[{idx}/{len(links)}] Memproses: {link}")
        ok = process_single_link(session, link, cookies_dict, history)
        if ok:
            successful_links += 1
        print("-" * 65)

    print("\n" + "=" * 65)
    print(f"[✓] Selesai! Berhasil memproses {successful_links}/{len(links)} tautan.")
    print(f"[✓] Semua berkas tersimpan di: {DOWNLOAD_DIR}")
    print("=" * 65)

if __name__ == "__main__":
    main()
