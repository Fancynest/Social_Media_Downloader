"""
Instagram Profile & Date Range Downloader
==========================================
Mengunduh seluruh postingan (foto, video, korsel, reels) dari profil pengguna
Instagram dengan dukungan penyaringan rentang waktu (DARI_TANGGAL s/d SAMPAI_TANGGAL).
"""

import os
import re
import sys
import time
import random
import getpass
import argparse
from datetime import datetime, date
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

import requests
import instaloader
from instaloader.exceptions import (
    ProfileNotExistsException,
    LoginRequiredException,
    PrivateProfileNotFollowedException,
    BadCredentialsException,
    TwoFactorAuthRequiredException,
    TooManyRequestsException,
    ConnectionException,
    QueryReturnedBadRequestException,
)

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
CONFIG_FILE = BASE_DIR / "input_target.txt"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
SESSION_FILE = BASE_DIR / "session.dat"
USER_FILE = BASE_DIR / "session_user.txt"


def extract_username(url_or_username: str) -> str:
    """Ekstrak username Instagram dari URL profil atau string biasa."""
    raw = url_or_username.strip()
    if not raw or raw.startswith("#"):
        return ""
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", raw)
    if m:
        u = m.group(1).rstrip("/").strip()
        return u if not u.startswith("#") else ""
    u = raw.lstrip("@").strip()
    return u if not u.startswith("#") else ""


def parse_date_filter(val: str) -> Optional[date]:
    """Parse string tanggal format YYYY-MM-DD atau YYYYMMDD menjadi datetime.date."""
    s = val.strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def read_config() -> Optional[Dict[str, Any]]:
    """Membaca konfigurasi target dan rentang tanggal dari input_target.txt."""
    if not CONFIG_FILE.exists():
        return None

    raw_targets = []
    target_block = False
    dari_tanggal = None
    sampai_tanggal = None
    max_posts = 0
    save_caption = False

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped = line.strip()

            if stripped.startswith("#"):
                continue

            if not stripped:
                continue

            upper = stripped.upper()
            if upper.startswith("DARI_TANGGAL"):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    dari_tanggal = parse_date_filter(parts[1])
                target_block = False
                continue

            if upper.startswith("SAMPAI_TANGGAL"):
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    sampai_tanggal = parse_date_filter(parts[1])
                target_block = False
                continue

            if upper.startswith("TARGET_AKUN") or upper.startswith("TARGET_ACCOUNTS"):
                target_block = True
                parts = stripped.split("=", 1)
                if len(parts) == 2 and parts[1].strip():
                    items = re.split(r"[,\s]+", parts[1].strip())
                    raw_targets.extend([it for it in items if it and not it.startswith("#")])
                continue

            if upper.startswith("MAKSIMAL_POST"):
                target_block = False
                parts = stripped.split("=", 1)
                if len(parts) == 2 and parts[1].strip():
                    try:
                        max_posts = int(parts[1].strip())
                    except ValueError:
                        max_posts = 0
                continue

            if upper.startswith("SIMPAN_CAPTION"):
                target_block = False
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    val = parts[1].strip().lower()
                    save_caption = val in ("ya", "y", "yes", "true", "1")
                continue

            if target_block:
                items = re.split(r"[,\s]+", stripped)
                raw_targets.extend([it for it in items if it and not it.startswith("#")])

    targets = []
    for item in raw_targets:
        u = extract_username(item)
        if u and u not in targets:
            targets.append(u)

    if not targets:
        return None

    return {
        "targets": targets,
        "dari_tanggal": dari_tanggal,
        "sampai_tanggal": sampai_tanggal,
        "max_posts": max_posts,
        "save_caption": save_caption,
    }


def prompt_user_input() -> Dict[str, Any]:
    """Menanyakan konfigurasi target secara interaktif jika input_target.txt kosong."""
    print("\n" + "=" * 60)
    print("      KONFIGURASI TARGET DOWNLOAD PROFIL INSTAGRAM")
    print("=" * 60)

    targets = []
    while not targets:
        raw = input("\nMasukkan Username/Link Akun Target (bisa dipisahkan koma/spasi):\n> ")
        items = re.split(r"[,\s]+", raw.strip())
        for it in items:
            u = extract_username(it)
            if u and u not in targets:
                targets.append(u)
        if not targets:
            print("[!] Minimal masukkan 1 target yang valid.")

    raw_dari = input("Batas Tanggal Awal (YYYY-MM-DD, kosongkan jika dari awal): ").strip()
    dari_tanggal = parse_date_filter(raw_dari)

    raw_sampai = input("Batas Tanggal Akhir (YYYY-MM-DD, kosongkan jika sampai terbaru): ").strip()
    sampai_tanggal = parse_date_filter(raw_sampai)

    raw_max = input("Maksimal postingan per akun (isi 0 atau Enter untuk SEMUA): ").strip()
    try:
        max_posts = int(raw_max) if raw_max else 0
    except ValueError:
        max_posts = 0

    raw_cap = input("Simpan teks caption ke file .txt? (y/N, default N): ").strip().lower()
    save_caption = raw_cap in ("y", "ya", "yes", "true", "1")

    return {
        "targets": targets,
        "dari_tanggal": dari_tanggal,
        "sampai_tanggal": sampai_tanggal,
        "max_posts": max_posts,
        "save_caption": save_caption,
    }


def parse_cookies_from_text(cookie_text: str) -> dict:
    """Membaca cookies format Netscape (ekstensi browser) atau raw format (sessionid=...)."""
    cookies = {}
    if not cookie_text:
        return cookies

    for line in cookie_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "\t" in line:
            parts = line.split("\t")
            if len(parts) >= 7:
                cookies[parts[5]] = parts[6]
        elif "=" in line:
            k, v = line.split("=", 1)
            cookies[k.strip()] = v.strip().strip(";\"'")

    if not cookies and len(cookie_text) > 15 and "\n" not in cookie_text:
        cookies["sessionid"] = cookie_text.strip().strip(";\"'")

    return cookies


def parse_cookie_file(cookie_path: Path) -> dict:
    if not cookie_path.exists():
        return {}
    content = cookie_path.read_text(encoding="utf-8", errors="ignore").strip()
    return parse_cookies_from_text(content)


def verify_and_get_username(cookies: dict) -> Tuple[bool, Optional[str]]:
    """Memverifikasi validitas cookies ke Instagram web dan mendeteksi username akun."""
    session = requests.Session()
    for domain in [".instagram.com", "instagram.com", "www.instagram.com"]:
        for k, v in cookies.items():
            session.cookies.set(k, v, domain=domain, path="/")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    try:
        r = session.get("https://www.instagram.com/", headers=headers, timeout=12)
        if r.status_code == 200:
            m = re.search(r'"username":\s*"([^"]+)"', r.text)
            if m:
                return True, m.group(1)
            if '"viewerId":' in r.text or "viewer" in r.text or "is_logged_in" in r.text:
                return True, None
    except Exception:
        pass
    return False, None


def login_interactive():
    print("=" * 60)
    print("      AUTENTIKASI AKUN INSTAGRAM (COOKIE / SESI)")
    print("=" * 60)
    print("1. Melalui Notepad 'input_cookie.txt' (Rekomendasi - Ekstensi Cookies / sessionid)")
    print("2. Login interaktif (Username & Password)\n")

    choice = input("Pilih metode (1/2, default 1): ").strip()
    if choice != "2":
        cookie_text = ""
        if COOKIE_FILE.exists():
            cookie_text = COOKIE_FILE.read_text(encoding="utf-8", errors="ignore").strip()

        is_empty = not cookie_text or all(line.strip().startswith("#") or not line.strip() for line in cookie_text.splitlines())
        if is_empty:
            print("[*] Membuka Notepad 'input_cookie.txt'...")
            print("[*] Silakan paste teks cookies dari browser Anda, lalu simpan (Ctrl+S).")
            try:
                os.system(f'notepad.exe "{COOKIE_FILE}"')
            except Exception:
                pass
            input("\nTekan Enter setelah selesai menyimpan cookies di Notepad...")
            if COOKIE_FILE.exists():
                cookie_text = COOKIE_FILE.read_text(encoding="utf-8", errors="ignore").strip()

        cookies = parse_cookies_from_text(cookie_text)
        session_id = cookies.get("sessionid")

        if not session_id:
            print("\n[x] Tidak ditemukan 'sessionid' pada input_cookie.txt.")
            print("    Pastikan Anda sudah login ke instagram.com di browser sebelum menyalin cookies.")
            return

        print("\n[*] Memverifikasi cookies ke server Instagram...")
        is_valid, detected_user = verify_and_get_username(cookies)

        if not is_valid:
            print("\n[x] Cookies tidak valid atau sesi browser telah kedaluwarsa.")
            print("    Silakan refresh halaman instagram.com di browser dan salin cookies terbaru.")
            return

        username = detected_user
        if not username:
            uid = cookies.get("ds_user_id", "")
            print(f"\n[✓] Cookies valid terverifikasi (User ID: {uid})!")
            raw_u = input("Masukkan username akun Instagram Anda: ").strip()
            username = extract_username(raw_u) or f"user_{uid}"

        loader = instaloader.Instaloader()
        for domain in [".instagram.com", "instagram.com"]:
            for k, v in cookies.items():
                loader.context._session.cookies.set(k, v, domain=domain, path="/")
        loader.context.username = username

        try:
            loader.save_session_to_file(str(SESSION_FILE))
            USER_FILE.write_text(username, encoding="utf-8")
            print(f"\n[✓] BERHASIL LOGIN sebagai @{username}!")
            print(f"[✓] Sesi login tersimpan pada: {SESSION_FILE.name}")
        except Exception as e:
            print(f"\n[x] Gagal menyimpan sesi login: {e}")
        return

    username = input("Username Instagram: ").strip()
    if not username:
        return
    password = getpass.getpass("Password Instagram: ")
    if not password:
        return

    loader = instaloader.Instaloader()
    try:
        loader.login(username, password)
        loader.save_session_to_file(str(SESSION_FILE))
        USER_FILE.write_text(username, encoding="utf-8")
        print(f"[✓] Berhasil login sebagai @{username}. Sesi disimpan.")
    except Exception as e:
        print(f"[x] Gagal login via password: {e}")
        print("    Tips: Gunakan metode 1 (Cookies) jika Instagram memblokir login terminal.")


def get_instaloader_instance(save_caption: bool = False) -> instaloader.Instaloader:
    """Membuat instance Instaloader dengan validasi sesi aktif."""
    loader = instaloader.Instaloader(
        sleep=False,
        download_pictures=True,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="{caption}" if save_caption else "",
        filename_pattern="{date_utc:%Y-%m-%d_%H-%M-%S}_{shortcode}",
    )

    session_candidates = [
        (SESSION_FILE, USER_FILE),
        (BASE_DIR.parent / "session.dat", BASE_DIR.parent / "session_user.txt"),
        (BASE_DIR.parent / "1_Filter_Berdasarkan_Keyword" / "session.dat", BASE_DIR.parent / "1_Filter_Berdasarkan_Keyword" / "session_user.txt"),
    ]

    for s_file, u_file in session_candidates:
        if s_file.exists() and u_file.exists():
            try:
                username = u_file.read_text(encoding="utf-8").strip()
                if username:
                    test_ldr = instaloader.Instaloader()
                    test_ldr.load_session_from_file(username, str(s_file))
                    # Validasi login
                    logged_user = test_ldr.test_login()
                    if logged_user:
                        print(f"[*] Menggunakan sesi login akun: @{logged_user}")
                        test_ldr.save_metadata = False
                        test_ldr.download_video_thumbnails = False
                        test_ldr.post_metadata_txt_pattern = "{caption}" if save_caption else ""
                        test_ldr.filename_pattern = "{date_utc:%Y-%m-%d_%H-%M-%S}_{shortcode}"
                        return test_ldr
                    else:
                        print(f"[!] Sesi login tersimpan (@{username}) telah kedaluwarsa.")
                        print("    Menghapus sesi usang dan beralih ke Mode Tamu publik...")
                        try:
                            s_file.unlink()
                            u_file.unlink()
                        except Exception:
                            pass
            except Exception:
                pass

    # Cek cookies dari input_cookie.txt jika ada
    cookies = parse_cookie_file(COOKIE_FILE)
    if "sessionid" in cookies:
        try:
            for domain in [".instagram.com", "instagram.com"]:
                for k, v in cookies.items():
                    loader.context._session.cookies.set(k, v, domain=domain, path="/")
            print("[*] Menggunakan cookie sesi dari input_cookie.txt")
            return loader
        except Exception:
            pass

    print("[*] Berjalan dalam Mode Tamu publik (tanpa login).")
    return loader


def main():
    parser = argparse.ArgumentParser(description="Instagram Profile & Date Range Downloader")
    parser.add_argument("--login", action="store_true", help="Jalankan autentikasi login Instagram")
    args = parser.parse_args()

    if args.login:
        login_interactive()
        input("\nTekan Enter untuk keluar...")
        return

    print("=" * 65)
    print("     INSTAGRAM ALL POSTS & DATE RANGE DOWNLOADER")
    print("=" * 65)

    config = read_config()
    if config:
        print(f"[*] Ditemukan konfigurasi {len(config['targets'])} akun target:")
        for t in config["targets"][:5]:
            print(f"    - @{t}")
        if len(config["targets"]) > 5:
            print(f"    ... dan {len(config['targets']) - 5} akun lainnya.")

        d_str = config["dari_tanggal"].strftime("%Y-%m-%d") if config.get("dari_tanggal") else "Awal Pembuatan"
        s_str = config["sampai_tanggal"].strftime("%Y-%m-%d") if config.get("sampai_tanggal") else "Terbaru"
        print(f"[*] Rentang Waktu  : {d_str} s/d {s_str}")
        print(f"[*] Maksimal Post  : {config['max_posts'] if config['max_posts'] > 0 else 'Semua (Tanpa Batas)'}")
        print(f"[*] Simpan Caption : {'Ya' if config.get('save_caption') else 'Tidak'}")

        pilihan = input("\nJalankan dengan pengaturan ini? (Y/n): ").strip().lower()
        if pilihan in ("n", "no"):
            config = prompt_user_input()
    else:
        config = prompt_user_input()

    targets = config["targets"]
    dari_tanggal = config.get("dari_tanggal")
    sampai_tanggal = config.get("sampai_tanggal")
    max_posts = config["max_posts"]
    save_caption = config.get("save_caption", False)

    loader = get_instaloader_instance(save_caption=save_caption)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_acc = len(targets)
    summary_report = []

    for idx, target in enumerate(targets, 1):
        print("\n" + "=" * 65)
        print(f" [{idx}/{total_acc}] MEMPROSES PROFIL: @{target}")
        print("=" * 65)

        target_dir = OUTPUT_DIR / target
        target_dir.mkdir(parents=True, exist_ok=True)

        try:
            profile = instaloader.Profile.from_username(loader.context, target)
            full_name = getattr(profile, "full_name", target)
            try:
                media_count = profile.mediacount
            except Exception:
                media_count = "Tersedia"
        except ProfileNotExistsException:
            print(f"[x] Akun @{target} tidak ditemukan. Melanjutkan ke target berikutnya...")
            summary_report.append({"target": target, "downloaded": 0, "status": "Tidak Ditemukan"})
            continue
        except LoginRequiredException:
            print(f"[x] Akun @{target} memerlukan login. Jalankan LOGIN_AKUN.bat.")
            summary_report.append({"target": target, "downloaded": 0, "status": "Perlu Login"})
            continue
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "wait a few minutes" in err_str or "429" in err_str:
                print(f"[!] Akses profil @{target} dibatasi sementara oleh Instagram (Rate Limit / 401).")
                print("    Solusi Cepat:")
                print("    1. Jika memakai Hotspot HP: Nyalakan Mode Pesawat selama 5 detik lalu matikan lagi.")
                print("    2. Atau login akun via LOGIN_AKUN.bat menggunakan cookie sessionid aktif.")
            else:
                print(f"[x] Gagal mengakses profil @{target}: {e}")
            summary_report.append({"target": target, "downloaded": 0, "status": "Rate Limit / Error"})
            continue

        print(f"[+] Nama Akun      : {full_name} (@{target})")
        print(f"[+] Total Postingan: {media_count}")
        print(f"[+] Direktori      : {target_dir}")
        print("-" * 65)

        scanned = 0
        downloaded = 0
        stopped_early = False
        rate_limited = False

        try:
            for post in profile.get_posts():
                scanned += 1
                post_dt = post.date_local.date()
                date_str = post.date_local.strftime("%Y-%m-%d %H:%M")
                media_type = "Video/Reel" if post.is_video else "Foto/Korsel"

                print(f"[{scanned}] [{date_str}] [{media_type}] {post.shortcode}")

                # Filter batas akhir (terbaru)
                if sampai_tanggal and post_dt > sampai_tanggal:
                    print(f"    [-] Tanggal postingan ({post_dt}) > batas akhir {sampai_tanggal}, dilewati.")
                    print("-" * 65)
                    continue

                # Filter batas awal (tertua) -> terminasi awal karena urutan descending
                if dari_tanggal and post_dt < dari_tanggal:
                    print(f"    [*] Tanggal postingan ({post_dt}) < batas awal {dari_tanggal}.")
                    print(f"    [✓] Seluruh postingan dalam rentang waktu untuk @{target} telah selesai dipindai!")
                    print("-" * 65)
                    break

                downloaded += 1
                print(f"    >>> Mengunduh postingan ke folder Hasil_Download/{target} ...")
                try:
                    loader.download_post(post, target=target_dir)
                    print("    [✓] Berhasil diunduh.")
                except Exception as dl_err:
                    print(f"    [!] Kendala saat mengunduh: {dl_err}")

                print("-" * 65)

                if max_posts > 0 and downloaded >= max_posts:
                    print(f"[*] Batas maksimal {max_posts} postingan untuk @{target} tercapai.")
                    break

                time.sleep(random.uniform(1.2, 1.8))

        except KeyboardInterrupt:
            print(f"\n[!] Proses pemindaian @{target} dihentikan oleh pengguna.")
            stopped_early = True
        except PrivateProfileNotFollowedException:
            print(f"\n[x] Akun @{target} bersifat privat dan akun Anda belum mem-follow akun ini.")
        except TooManyRequestsException:
            print("\n[!] Rate limit Instagram tercapai (429 Too Many Requests).")
            print("    Tips: Nyalakan Mode Pesawat di HP selama 5 detik lalu matikan lagi untuk ganti IP.")
            rate_limited = True
        except Exception as e:
            err_str = str(e)
            if "401" in err_str or "wait a few minutes" in err_str or "429" in err_str:
                print("\n[!] Rate limit Instagram tercapai (401 Unauthorized / Too Many Requests).")
                print("    Instagram membatasi permintaan dari alamat IP Anda saat ini.")
                print("    Tips: Nyalakan Mode Pesawat di HP selama 5 detik lalu matikan lagi untuk ganti IP baru.")
                rate_limited = True
            else:
                print(f"\n[x] Terjadi kendala saat memindai: {e}")

        summary_report.append({
            "target": target,
            "downloaded": downloaded,
            "status": "Selesai" if not rate_limited else "Rate limit"
        })

        if stopped_early or rate_limited:
            break

        if idx < total_acc:
            print("\n[*] Jeda 5 detik sebelum memproses akun berikutnya...")
            time.sleep(5)

    print("\n" + "=" * 65)
    print("                 RINGKASAN PROSES DOWNLOAD")
    print("=" * 65)
    for r in summary_report:
        print(f" - @{r['target']:<20} : {r['downloaded']} postingan diunduh ({r['status']})")
    print("=" * 65)
    print(f"[✓] Semua proses selesai. Berkas tersimpan di: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
