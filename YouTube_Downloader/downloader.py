# -*- coding: utf-8 -*-
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
    # 1. Cek apakah ada input_cookie.txt yang sudah diisi
    if COOKIE_INPUT.exists() and COOKIE_INPUT.stat().st_size > 20:
        raw_text = COOKIE_INPUT.read_text(encoding="utf-8", errors="ignore").strip()
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

    # 2. Cek apakah ada cookies.txt langsung di folder
    if COOKIE_DIRECT.exists() and COOKIE_DIRECT.stat().st_size > 20:
        return COOKIE_DIRECT

    return None


def clean_url(raw_url: str) -> str:
    url = raw_url.strip()
    if url.startswith("@"):
        return f"https://www.youtube.com/{url}"
    return url


def parse_date_str(val: str) -> str:
    # Bersihkan string tanggal ke format YYYYMMDD
    cleaned = re.sub(r"[^\d]", "", val.strip())
    if len(cleaned) == 8:
        return cleaned
    return ""


def load_links_and_settings():
    if not TXT_FILE.exists():
        with open(TXT_FILE, "w", encoding="utf-8") as f:
            f.write("# Tempelkan tautan video YouTube di sini (1 per baris):\n")
        return [], "", ""

    links = []
    dari_tanggal = ""
    sampai_tanggal = ""

    with open(TXT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("//"):
                continue

            # Deteksi pengaturan rentang waktu
            if "=" in line:
                k, v = line.split("=", 1)
                k_clean = k.strip().upper()
                v_clean = v.strip()
                if k_clean == "DARI_TANGGAL":
                    dari_tanggal = parse_date_str(v_clean)
                    continue
                elif k_clean == "SAMPAI_TANGGAL":
                    sampai_tanggal = parse_date_str(v_clean)
                    continue

            cleaned = clean_url(line)
            if cleaned.startswith("http://") or cleaned.startswith("https://"):
                links.append(cleaned)

    return links, dari_tanggal, sampai_tanggal


def is_channel_or_playlist(url: str) -> bool:
    channel_markers = ["/@", "/channel/", "/c/", "/user/", "/playlist?list="]
    return any(marker in url for marker in channel_markers)


def run_download():
    print("=" * 60)
    print("      YOUTUBE MASS MEDIA DOWNLOADER (HD / 2K / 4K)")
    print("=" * 60)
    print(" Format   : MP4 Kualitas Terbaik (Auto Merge Video + Audio)")
    print(" Dukungan : Video Standar, Shorts, Playlist & Full Channel (@)")
    print("=" * 60)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    active_cookie = prepare_clean_cookie_file()
    has_cookie = False

    try:
        import yt_dlp
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], check=False)
        import yt_dlp

    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'windowsfilenames': True,
        'download_archive': str(ARCHIVE_FILE),
        'no_warnings': True,
        'ignoreerrors': False,
    }

    if active_cookie:
        ydl_opts['cookiefile'] = str(active_cookie)
        has_cookie = True
        print(f"[+] Cookies aktif : '{COOKIE_INPUT.name}' dimuat (Bypass batasan usia & 18+)")
    else:
        firefox_dir = Path(os.environ.get("APPDATA", "")) / "Mozilla" / "Firefox" / "Profiles"
        if firefox_dir.exists() and any(firefox_dir.glob("*")):
            try:
                ydl_opts['cookiesfrombrowser'] = ('firefox',)
                has_cookie = True
                print("[+] Cookies aktif : Terdeteksi otomatis dari browser Firefox")
            except Exception:
                pass

    if not has_cookie:
        print("[i] Mode Tamu     : Berjalan tanpa cookies")
        print("    Tips: Jika ada video batasan usia (18+) yang gagal diunduh,")
        print("    tempelkan cookies ke 'input_cookie.txt' (klik BUKA_NOTEPAD_COOKIE.bat).")

    links, dari_tgl, sampai_tgl = load_links_and_settings()

    if dari_tgl or sampai_tgl:
        t_dari = f"{dari_tgl[:4]}-{dari_tgl[4:6]}-{dari_tgl[6:]}" if len(dari_tgl) == 8 else "Awal"
        t_sampai = f"{sampai_tgl[:4]}-{sampai_tgl[4:6]}-{sampai_tgl[6:]}" if len(sampai_tgl) == 8 else "Sekarang"
        print(f"[+] Rentang Waktu : {t_dari} s/d {t_sampai}")
        if dari_tgl:
            ydl_opts['dateafter'] = dari_tgl
        if sampai_tgl:
            ydl_opts['datebefore'] = sampai_tgl
    else:
        print("[+] Rentang Waktu : Semua Postingan (Tanpa Batas Tanggal)")

    if not links:
        print(f"\n[!] '{TXT_FILE.name}' masih kosong atau belum ada tautan valid.")
        print("[*] Silakan isi tautan ke berkas tersebut lalu simpan (Ctrl+S).")
        try:
            os.system(f'notepad.exe "{TXT_FILE}"')
        except Exception:
            pass
        input("\nTekan Enter setelah selesai mengisi tautan...")
        links, dari_tgl, sampai_tgl = load_links_and_settings()
        if not links:
            print("[!] Tidak ada tautan untuk diproses.")
            return

    print(f"\n Folder Simpan : {OUTPUT_DIR}")
    print(f" Total Tautan  : {len(links)}\n")

    success_count, fail_count = 0, 0

    for idx, url in enumerate(links, 1):
        print("-" * 60)
        print(f"[{idx}/{len(links)}] Memproses: {url}")

        opts = dict(ydl_opts)
        if is_channel_or_playlist(url):
            opts['noplaylist'] = False
            opts['outtmpl'] = str(OUTPUT_DIR / "%(uploader)s" / "%(upload_date)s - %(title).70s [%(id)s].%(ext)s")
            print("  [*] Mode Deteksi: Channel / Playlist (Mengunduh semua video yang tersedia)...")
        else:
            opts['noplaylist'] = True
            opts['outtmpl'] = str(OUTPUT_DIR / "%(uploader)s - %(title).70s [%(id)s].%(ext)s")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                ret = ydl.download([url])
                if ret == 0:
                    print("  [✓] Berhasil diproses.")
                    success_count += 1
                else:
                    print("  [x] Gagal mengunduh.")
                    fail_count += 1
        except Exception as e:
            err_msg = str(e)
            print(f"  [x] Error: {err_msg}")
            if any(k in err_msg.lower() for k in ["confirm your age", "age-restricted", "sign in to confirm", "inappropriate for some users"]):
                print("\n  [!] PERHATIAN: Video ini memerlukan autentikasi batasan usia (18+).")
                print("      Solusi:")
                print("      1. Klik 2x file 'BUKA_NOTEPAD_COOKIE.bat'.")
                print("      2. Tempelkan cookies akun YouTube Anda, lalu simpan (Ctrl+S).")
                print("      3. Jalankan ulang DOWNLOAD_SEKARANG.bat.\n")
            fail_count += 1

    print("\n" + "=" * 60)
    print("                    RINGKASAN PENGUNDUHAN")
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
