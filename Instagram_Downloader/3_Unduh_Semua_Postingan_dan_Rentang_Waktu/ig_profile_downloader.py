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

try:
    import requests
    import instaloader
except ImportError:
    import subprocess
    print("[*] Menyiapkan paket library (instaloader & requests)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "instaloader>=4.10", "requests>=2.28.0"])
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


def _patch_instaloader():
    """
    Patch Instaloader Context dan Profile:
    1. Patch _web_api_tokens agar tidak melempar BadResponseException jika fb_dtsg belum termuat.
    2. Patch doc_id_graphql_query agar selalu menggunakan web_api=True.
    3. Patch Profile.from_username agar selalu menormalkan metadata node (_normalize_profile_data).
    4. Patch test_login agar mendeteksi sesi web langsung tanpa query_hash legacy GraphQL.
    """
    # 1. Patch _web_api_tokens
    def patched_web_api_tokens(self):
        sessionid = self._session.cookies.get_dict().get("sessionid", "")
        if sessionid not in self._web_api_tokens_cache:
            html = self._get_page(self._session, "")
            tokens = {}
            for name, patterns in [
                ("fb_dtsg", [
                    r'"DTSGInitialData",\[\],\{[^{}]*"token":"([^"]+)"',
                    r'"DTSGInitData",\[\],\{[^{}]*"token":"([^"]+)"',
                    r'"dtsg":\{"token":"([^"]+)"',
                ]),
                ("lsd", [
                    r'"LSD",\[\],\{[^{}]*"token":"([^"]+)"',
                ]),
                ("av", [
                    r'"IG_USER_EIMU":"?(\d+)',
                    r'"actor_id":"?(\d+)',
                ]),
            ]:
                for pattern in patterns:
                    m = re.search(pattern, html)
                    if m and m.group(1):
                        tokens[name] = m.group(1)
                        break
            if self.is_logged_in and not tokens.get("fb_dtsg"):
                raise LoginRequiredException("Sesi login Instagram kedaluwarsa (token fb_dtsg kosong).")
            self._web_api_tokens_cache[sessionid] = tokens
        return self._web_api_tokens_cache.get(sessionid, {})

    instaloader.InstaloaderContext._web_api_tokens = patched_web_api_tokens

    # 2. Patch doc_id_graphql_query
    orig_doc_id = instaloader.InstaloaderContext.doc_id_graphql_query

    def patched_doc_id(self, doc_id: str, variables: dict, referer: Optional[str] = None, web_api: bool = True):
        return orig_doc_id(self, doc_id, variables, referer=referer, web_api=True)

    instaloader.InstaloaderContext.doc_id_graphql_query = patched_doc_id

    # 3. Patch Profile.from_username
    orig_from_username = instaloader.Profile.from_username

    def patched_from_username(cls, context, username: str):
        profile = None
        try:
            profile = orig_from_username(context, username)
        except Exception:
            if not context.is_logged_in:
                raise
            try:
                html = context._get_page(context._session, f"{username.lower()}/")
            except Exception:
                raise ProfileNotExistsException(f"Profile {username} does not exist.")

            if "Sorry, this page isn't available" in html or "Halaman ini tidak tersedia" in html:
                raise ProfileNotExistsException(f"Profile {username} does not exist.")

            m_pid = re.findall(r'"profile_id":"(\d+)"', html)
            if not m_pid:
                m_pid = re.findall(r'"page_id":"profilePage_(\d+)"', html)
            if not m_pid:
                m_pid = re.findall(r'"props":\{"id":"(\d+)"', html)

            if m_pid:
                pid = m_pid[0]
                node = {"id": str(pid), "pk": int(pid), "username": username.lower()}
                profile = cls(context, node)
            else:
                raise ProfileNotExistsException(f"Profile {username} does not exist.")

        if profile and hasattr(profile, "_node") and isinstance(profile._node, dict):
            profile._node = cls._normalize_profile_data(profile._node)

        return profile

    instaloader.Profile.from_username = classmethod(patched_from_username)

    # 4. Patch test_login agar mendeteksi sesi web langsung
    def patched_test_login(self) -> Optional[str]:
        cookie_dict = {c.name: c.value for c in self._session.cookies if c.value}
        if not cookie_dict.get("sessionid"):
            return None

        target_name = getattr(self, "username", "") or ""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
        }
        try:
            probe_sess = requests.Session()
            for k, v in cookie_dict.items():
                probe_sess.cookies.set(k, v, domain=".instagram.com", path="/")
            resp = probe_sess.get("https://www.instagram.com/", headers=headers, timeout=12, allow_redirects=False)
            if resp.status_code != 200:
                return None

            idx = resp.text.find('["PolarisViewer"')
            if idx != -1:
                snippet = resp.text[idx : idx + 4000]
                m = re.search(r'"username":"([^"]+)"', snippet)
                if m:
                    self.username = m.group(1)
                    return m.group(1)

            m_viewer = re.search(r'"viewer":\s*\{[^}]*?"username":"([^"]+)"', resp.text)
            if m_viewer:
                self.username = m_viewer.group(1)
                return m_viewer.group(1)

            if re.search(r'"DTSGInitialData",\[\],\{[^{}]*"token":"([^"]+)"', resp.text):
                uid = cookie_dict.get("ds_user_id")
                val = target_name or (f"user_{uid}" if uid else "logged_in_user")
                self.username = val
                return val
        except Exception:
            return None

        return None

    instaloader.InstaloaderContext.test_login = patched_test_login


_patch_instaloader()

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
    if "?" in raw:
        raw = raw.split("?")[0]
    m = re.search(r"instagram\.com/([A-Za-z0-9_.]+)", raw)
    if m:
        u = m.group(1).rstrip("/").strip()
        return u if not u.startswith("#") else ""
    u = raw.lstrip("@").strip().rstrip("/")
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
    media_type = "semua"

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

            if upper.startswith("TIPE_MEDIA") or upper.startswith("MEDIA_TYPE"):
                target_block = False
                parts = stripped.split("=", 1)
                if len(parts) == 2:
                    val = parts[1].strip().lower()
                    if val in ("foto", "photo", "image", "gambar"):
                        media_type = "foto"
                    elif val in ("video", "vid", "reel", "reels"):
                        media_type = "video"
                    else:
                        media_type = "semua"
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
        "media_type": media_type,
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

    raw_media = input("Filter Tipe Media (semua/foto/video, default semua): ").strip().lower()
    if raw_media in ("foto", "photo", "image", "gambar"):
        media_type = "foto"
    elif raw_media in ("video", "vid", "reel", "reels"):
        media_type = "video"
    else:
        media_type = "semua"

    return {
        "targets": targets,
        "dari_tanggal": dari_tanggal,
        "sampai_tanggal": sampai_tanggal,
        "max_posts": max_posts,
        "save_caption": save_caption,
        "media_type": media_type,
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
    for k, v in cookies.items():
        session.cookies.set(k, v, domain=".instagram.com", path="/")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    }
    try:
        r = session.get("https://www.instagram.com/", headers=headers, timeout=12, allow_redirects=False)
        if r.status_code != 200:
            return False, None
        idx = r.text.find('["PolarisViewer"')
        if idx != -1:
            m = re.search(r'"username":"([^"]+)"', r.text[idx : idx + 4000])
            if m:
                return True, m.group(1)
        m_v = re.search(r'"viewer":\s*\{[^}]*?"username":"([^"]+)"', r.text)
        if m_v:
            return True, m_v.group(1)
        if re.search(r'"DTSGInitialData",\[\],\{[^{}]*"token":"([^"]+)"', r.text):
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
        loader.context._session.cookies.clear()
        for k, v in cookies.items():
            loader.context._session.cookies.set(k, v, domain=".instagram.com", path="/")
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


def get_instaloader_instance(save_caption: bool = False, media_type: str = "semua") -> instaloader.Instaloader:
    """Membuat instance Instaloader dengan validasi sesi aktif & proteksi anti-banned."""
    dl_pictures = media_type != "video"
    dl_videos = media_type != "foto"
    windows_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    loader = instaloader.Instaloader(
        sleep=True,
        user_agent=windows_ua,
        max_connection_attempts=2,
        download_pictures=dl_pictures,
        download_videos=dl_videos,
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
                    test_ldr = instaloader.Instaloader(sleep=True, user_agent=windows_ua, max_connection_attempts=2)
                    test_ldr.load_session_from_file(username, str(s_file))
                    # Validasi login
                    logged_user = test_ldr.test_login()
                    if logged_user:
                        print(f"[*] Menggunakan sesi login akun: @{logged_user}")
                        test_ldr.download_pictures = dl_pictures
                        test_ldr.download_videos = dl_videos
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
            loader.context._session.cookies.clear()
            for k, v in cookies.items():
                loader.context._session.cookies.set(k, v, domain=".instagram.com", path="/")
            logged_user = loader.test_login()
            if logged_user:
                loader.context.username = logged_user
                print(f"[*] Menggunakan cookie sesi aktif dari input_cookie.txt (@{logged_user})")
                return loader
            print("[!] Cookie di input_cookie.txt sudah kedaluwarsa/logout. Jalankan LOGIN_AKUN.bat.")
            loader.context._session.cookies.clear()
            loader.context.username = None
        except Exception:
            loader.context._session.cookies.clear()
            loader.context.username = None

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
        print(f"[*] Filter Media   : {config.get('media_type', 'semua').upper()}")

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
    filter_media = config.get("media_type", "semua")

    loader = get_instaloader_instance(save_caption=save_caption, media_type=filter_media)
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
            try:
                full_name = profile.full_name
            except Exception:
                full_name = target
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
                media_label = "Video/Reel" if post.is_video else "Foto/Korsel"

                print(f"[{scanned}] [{date_str}] [{media_label}] {post.shortcode}")

                # Filter tipe media (foto doang atau video doang)
                if filter_media == "video" and (post.typename == "GraphImage" or (not post.is_video and post.typename != "GraphSidecar")):
                    print(f"    [-] Postingan bertipe foto, dilewati (filter: video doang).")
                    print("-" * 65)
                    continue
                if filter_media == "foto" and post.typename == "GraphVideo":
                    print(f"    [-] Postingan bertipe video, dilewati (filter: foto doang).")
                    print("-" * 65)
                    continue

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
                    err_low = str(dl_err).lower()
                    print(f"    [!] Kendala saat mengunduh: {dl_err}")
                    if any(k in err_low for k in ("401", "429", "challenge", "checkpoint", "login", "wait a few minutes", "feedback_required")):
                        print("    [!] Deteksi pembatasan/challenge Instagram -> menghentikan sementara agar akun aman.")
                        rate_limited = True
                        break

                print("-" * 65)

                if max_posts > 0 and downloaded >= max_posts:
                    print(f"[*] Batas maksimal {max_posts} postingan untuk @{target} tercapai.")
                    break

                # Jeda aman anti-banned: jeda acak 3-5.5 detik per post & istirahat berkala setiap 15 post
                if downloaded % 15 == 0:
                    pause_s = random.uniform(20.0, 35.0)
                    print(f"    [*] Cooldown anti-limit {pause_s:.0f} detik (setelah {downloaded} post)...")
                    time.sleep(pause_s)
                else:
                    time.sleep(random.uniform(3.0, 5.5))

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
            if any(k in err_str.lower() for k in ("401", "wait a few minutes", "429", "challenge", "checkpoint")):
                print("\n[!] Rate limit / Challenge Instagram terdeteksi -> menghentikan agar akun aman.")
                print("    Tips: Istirahatkan akun beberapa jam atau ganti IP (Mode Pesawat di HP).")
                rate_limited = True
            else:
                print(f"\n[x] Terjadi kendala saat memindai: {e}")

        summary_report.append({
            "target": target,
            "downloaded": downloaded,
            "status": "Selesai" if not rate_limited else "Dihentikan (Aman)"
        })

        if stopped_early or rate_limited:
            break

        if idx < total_acc:
            acc_pause = random.uniform(12.0, 20.0)
            print(f"\n[*] Jeda {acc_pause:.0f} detik sebelum memproses akun berikutnya...")
            time.sleep(acc_pause)

    print("\n" + "=" * 65)
    print("                 RINGKASAN PROSES DOWNLOAD")
    print("=" * 65)
    for r in summary_report:
        print(f" - @{r['target']:<20} : {r['downloaded']} postingan diunduh ({r['status']})")
    print("=" * 65)
    print(f"[✓] Semua proses selesai. Berkas tersimpan di: {OUTPUT_DIR}\n")


if __name__ == "__main__":
    main()
