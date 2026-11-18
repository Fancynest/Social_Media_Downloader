"""
Instagram Follower & Following Scraper
========================================
Mengekstrak dan mengunduh daftar followers (pengikut) atau following (mengikuti)
dari akun Instagram target ke dalam format .txt dan .csv (Excel).
Mendukung sinkronisasi sesi login otomatis dari Instagram Downloader.
"""

import os
import re
import sys
import csv
import time
import random
import getpass
import argparse
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

# Auto-install dependencies if missing
try:
    import requests
    import instaloader
except ImportError:
    import subprocess
    print("[*] Menyiapkan library yang dibutuhkan (instaloader & requests)...")
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
    2. Patch Profile.from_username agar selalu menormalkan metadata node (_normalize_profile_data),
       sehingga KeyError 'edge_follow' / 'edge_followed_by' tidak pernah terjadi.
    """
    # 1. Patch _web_api_tokens
    def patched_web_api_tokens(self):
        try:
            sessionid = self._session.cookies.get_dict().get("sessionid", "")
            if sessionid not in self._web_api_tokens_cache:
                html = self._get_page(self._session, "")
                tokens = {}
                for name, patterns in [
                    ("fb_dtsg", [
                        r'"DTSGInitialData",\[\],\{[^{}]*"token":"([^"]+)"',
                        r'"DTSGInitData",\[\],\{[^{}]*"token":"([^"]+)"',
                        r'"token":"([a-zA-Z0-9_\-]+:\d+:\d+)"',
                        r'"dtsg":\{"token":"([^"]+)"',
                    ]),
                    ("lsd", [
                        r'"LSD",\[\],\{[^{}]*"token":"([^"]+)"',
                        r'"token":"([a-zA-Z0-9_\-]+)"',
                    ]),
                    ("av", [
                        r'"IG_USER_EIMU":"?(\d+)',
                        r'"actor_id":"?(\d+)',
                    ]),
                ]:
                    for pattern in patterns:
                        m = re.search(pattern, html)
                        if m:
                            tokens[name] = m.group(1)
                            break
                self._web_api_tokens_cache[sessionid] = tokens
            return self._web_api_tokens_cache.get(sessionid, {})
        except Exception:
            return {}

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
        except ProfileNotExistsException:
            if not context.is_logged_in:
                raise
            try:
                html = context._get_page(context._session, f"{username.lower()}/")
            except Exception:
                raise ProfileNotExistsException(f"Profil @{username} tidak ditemukan.")

            if "Sorry, this page isn't available" in html or "Halaman ini tidak tersedia" in html:
                raise ProfileNotExistsException(f"Profil @{username} tidak ditemukan.")

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
                raise ProfileNotExistsException(f"Profil @{username} tidak ditemukan.")

        if profile and hasattr(profile, "_node") and isinstance(profile._node, dict):
            profile._node = cls._normalize_profile_data(profile._node)
            profile._has_full_metadata = True

        return profile

    instaloader.Profile.from_username = classmethod(patched_from_username)

    # 4. Patch test_login agar tidak menggunakan query_hash legacy GraphQL (yang error 400 feedback_required)
    def patched_test_login(self) -> Optional[str]:
        cookie_dict = self._session.cookies.get_dict()
        if not cookie_dict.get("sessionid"):
            return None

        target_name = getattr(self, "username", "") or ""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        try:
            resp = self._session.get("https://www.instagram.com/", headers=headers, timeout=12, allow_redirects=True)
            if "accounts/login" in resp.url.lower():
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

            if resp.status_code == 200 and cookie_dict.get("ds_user_id"):
                return target_name or f"user_{cookie_dict.get('ds_user_id')}"
        except Exception:
            pass

        return target_name if target_name else None

    instaloader.InstaloaderContext.test_login = patched_test_login


_patch_instaloader()

# Konfigurasi path file & folder
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "Hasil_Scrape"
CONFIG_FILE = BASE_DIR / "input_target.txt"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
SESSION_FILE = BASE_DIR / "session.dat"
USER_FILE = BASE_DIR / "session_user.txt"


def ensure_cookie_template():
    """Pastikan input_cookie.txt selalu tersedia dengan petunjuk lengkap."""
    if not COOKIE_FILE.exists():
        with open(COOKIE_FILE, "w", encoding="utf-8") as f:
            f.write(
                "# ==============================================================================\n"
                "# TEMPELKAN (PASTE) TEKS COOKIES DARI EKSTENSI BROWSER DI SINI\n"
                "# ==============================================================================\n"
                "# Petunjuk Penggunaan:\n"
                "# 1. Buka instagram.com di Chrome / Edge (pastikan sudah login).\n"
                "# 2. Klik ekstensi 'Get cookies.txt LOCALLY' di pojok kanan atas browser.\n"
                "# 3. Klik tombol 'Export' atau salin seluruh teks cookies yang muncul.\n"
                "# 4. Tempelkan (paste) seluruh teks tersebut di file Notepad ini.\n"
                "# 5. Simpan file ini (tekan CTRL + S), lalu tutup Notepad.\n"
                "# 6. Klik 2x file 'LOGIN_AKUN.bat' untuk memverifikasi dan mengaktifkan sesi login!\n"
                "# ==============================================================================\n"
            )


def extract_username(url_or_username: str) -> str:
    """Mengekstrak username Instagram bersih dari URL profil atau string teks."""
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


def parse_cookies_from_text(cookie_text: str) -> dict:
    """Mengekstrak cookies Instagram dari format Netscape (.txt) atau teks mentah."""
    cookies = {}
    for line in cookie_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            domain, flag, path, secure, expiration, name, value = parts[:7]
            if "instagram.com" in domain.lower() or not domain:
                cookies[name.strip()] = value.strip()
        elif "=" in line and ";" not in line and " " not in line.strip():
            k, _, v = line.partition("=")
            cookies[k.strip()] = v.strip()
        elif ";" in line:
            for pair in line.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    k, _, v = pair.partition("=")
                    if k.strip():
                        cookies[k.strip()] = v.strip()
    return cookies


def verify_and_get_username(cookies: dict) -> Tuple[bool, Optional[str]]:
    """Memverifikasi validitas cookies ke Instagram web dan mendeteksi username akun."""
    session = requests.Session()
    for domain in [".instagram.com", "instagram.com", "www.instagram.com"]:
        for k, v in cookies.items():
            session.cookies.set(k, v, domain=domain, path="/")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-User": "?1",
        "Sec-Fetch-Dest": "document",
    }

    try:
        resp = session.get("https://www.instagram.com/", headers=headers, timeout=15, allow_redirects=True)
        if "accounts/login" in resp.url.lower():
            return False, None

        idx = resp.text.find('["PolarisViewer"')
        if idx != -1:
            snippet = resp.text[idx : idx + 4000]
            m = re.search(r'"username":"([^"]+)"', snippet)
            if m:
                return True, m.group(1)

        m_viewer = re.search(r'"viewer":\s*\{[^}]*?"username":"([^"]+)"', resp.text)
        if m_viewer:
            return True, m_viewer.group(1)

        uid = cookies.get("ds_user_id")
        if uid and uid in resp.text:
            m_uid = re.search(r'"username":"([^"]+)".*?"id":"' + re.escape(uid) + r'"', resp.text)
            if m_uid:
                return True, m_uid.group(1)
            m_uid2 = re.search(r'"id":"' + re.escape(uid) + r'".*?"username":"([^"]+)"', resp.text)
            if m_uid2:
                return True, m_uid2.group(1)
            return True, None

        if resp.status_code == 200 and uid:
            return True, None

    except Exception as e:
        print(f"     [!] Gagal verifikasi cookies: {e}")

    return False, None


def save_and_share_session(loader: instaloader.Instaloader, username: str):
    """Menyimpan sesi login di folder lokal dan membagikannya ke modul Instagram lain."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    loader.save_session_to_file(str(SESSION_FILE))
    with open(USER_FILE, "w", encoding="utf-8") as f:
        f.write(username)

    # Sinkronisasi ke folder Instagram_Downloader & parent
    sync_targets = [
        BASE_DIR.parent,
        BASE_DIR.parent.parent / "Instagram_Downloader",
        BASE_DIR.parent.parent / "Instagram_Downloader" / "1_Filter_Berdasarkan_Keyword",
        BASE_DIR.parent.parent / "Instagram_Downloader" / "2_Unduh_Banyak_Link",
        BASE_DIR.parent.parent / "Instagram_Downloader" / "3_Unduh_Semua_Postingan_dan_Rentang_Waktu",
    ]
    for target in sync_targets:
        if target.exists() and target.is_dir():
            try:
                loader.save_session_to_file(str(target / "session.dat"))
                with open(target / "session_user.txt", "w", encoding="utf-8") as uf:
                    uf.write(username)
            except Exception:
                pass


def login_interactive() -> bool:
    """Menangani alur login interaktif via Cookies Notepad atau Username & Password."""
    ensure_cookie_template()
    print("=" * 65)
    print(" AUTENTIKASI AKUN INSTAGRAM (COOKIE / SESI LOGIN)")
    print("=" * 65)
    print("1. Melalui Notepad 'input_cookie.txt' (Ekstensi 'Get cookies.txt' / sessionid)")
    print("2. Login langsung (Username & Password)\n")

    choice = input("Pilih metode login (1/2, default 1): ").strip()
    if choice != "2":
        cookie_text = ""
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                cookie_text = f.read().strip()

        is_empty = not cookie_text or all(
            line.strip().startswith("#") or not line.strip() for line in cookie_text.splitlines()
        )
        if is_empty:
            print("\n[*] Membuka Notepad 'input_cookie.txt'...")
            print("[*] Silakan paste teks cookies dari ekstensi browser Anda, lalu simpan (Ctrl+S).")
            try:
                os.system(f'notepad.exe "{COOKIE_FILE}"')
            except Exception:
                pass
            input("\nTekan Enter setelah selesai menyimpan cookies di Notepad...")

            if COOKIE_FILE.exists():
                with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    cookie_text = f.read().strip()

        cookies = parse_cookies_from_text(cookie_text)
        session_id = cookies.get("sessionid")

        if not session_id:
            print("\n[x] Tidak ditemukan 'sessionid' di input_cookie.txt.")
            print("    Pastikan Anda sudah login ke instagram.com sebelum mengekspor cookies.")
            return False

        print("\n[*] Memverifikasi cookies ke server Instagram...")
        is_valid, detected_user = verify_and_get_username(cookies)

        if not is_valid:
            print("\n[x] Cookies tidak valid atau sesi browser telah kedaluwarsa.")
            print("    Silakan buka instagram.com di browser, pastikan akun sudah login,")
            print("    lalu ekspor ulang cookies dan paste ke input_cookie.txt.")
            return False

        username = detected_user
        if not username:
            uid = cookies.get("ds_user_id", "")
            print(f"\n[✓] Cookies valid terverifikasi (User ID: {uid})!")
            raw_u = input("Masukkan username akun Instagram Anda untuk melengkapi sesi: ").strip()
            username = extract_username(raw_u) or f"user_{uid}"

        loader = instaloader.Instaloader(sleep=False)
        for domain in [".instagram.com", "instagram.com"]:
            for k, v in cookies.items():
                loader.context._session.cookies.set(k, v, domain=domain, path="/")
        loader.context.username = username

        try:
            save_and_share_session(loader, username)
            print(f"\n[✓] BERHASIL LOGIN sebagai @{username}!")
            print(f"[✓] Sesi login tersimpan pada: {SESSION_FILE.name}")
            print("    Sesi ini juga otomatis terhubung ke folder downloader lainnya.")
            return True
        except Exception as e:
            print(f"\n[x] Gagal menyimpan sesi login: {e}")
            return False

    username = input("Username Instagram: ").strip()
    if not username:
        return False
    password = getpass.getpass("Password Instagram: ")
    if not password:
        return False

    loader = instaloader.Instaloader(sleep=False)
    try:
        loader.login(username, password)
        save_and_share_session(loader, username)
        print(f"\n[✓] Berhasil login sebagai @{username}. Sesi disimpan.")
        return True
    except TwoFactorAuthRequiredException:
        code = input("Kode 2FA: ").strip()
        try:
            loader.two_factor_login(code)
            save_and_share_session(loader, username)
            print("\n[✓] Login 2FA berhasil. Sesi disimpan.")
            return True
        except Exception as e:
            print(f"\n[x] Verifikasi 2FA gagal: {e}")
            return False
    except BadCredentialsException:
        print("\n[x] Username atau password salah.")
        return False
    except Exception as e:
        if "Checkpoint required" in str(e):
            print("\n[!] Akun terkena checkpoint. Buka aplikasi Instagram di HP lalu pilih 'Ini Saya'.")
        else:
            print(f"\n[x] Gagal login: {e}")
        return False


def get_authenticated_loader() -> Optional[instaloader.Instaloader]:
    """
    Memuat sesi Instagram aktif.
    Memeriksa folder lokal, folder parent, dan seluruh modul Instagram_Downloader.
    """
    loader = instaloader.Instaloader(
        sleep=False,
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
    )

    search_locations = [
        (SESSION_FILE, USER_FILE),
        (BASE_DIR.parent / "session.dat", BASE_DIR.parent / "session_user.txt"),
        (BASE_DIR.parent.parent / "Instagram_Downloader" / "session.dat",
         BASE_DIR.parent.parent / "Instagram_Downloader" / "session_user.txt"),
        (BASE_DIR.parent.parent / "Instagram_Downloader" / "1_Filter_Berdasarkan_Keyword" / "session.dat",
         BASE_DIR.parent.parent / "Instagram_Downloader" / "1_Filter_Berdasarkan_Keyword" / "session_user.txt"),
        (BASE_DIR.parent.parent / "Instagram_Downloader" / "2_Unduh_Banyak_Link" / "session.dat",
         BASE_DIR.parent.parent / "Instagram_Downloader" / "2_Unduh_Banyak_Link" / "session_user.txt"),
        (BASE_DIR.parent.parent / "Instagram_Downloader" / "3_Unduh_Semua_Postingan_dan_Rentang_Waktu" / "session.dat",
         BASE_DIR.parent.parent / "Instagram_Downloader" / "3_Unduh_Semua_Postingan_dan_Rentang_Waktu" / "session_user.txt"),
    ]

    for s_file, u_file in search_locations:
        if s_file.exists() and u_file.exists():
            try:
                with open(u_file, "r", encoding="utf-8") as uf:
                    saved_user = uf.read().strip()
                if saved_user:
                    test_ldr = instaloader.Instaloader(sleep=False)
                    test_ldr.load_session_from_file(saved_user, str(s_file))
                    logged_user = test_ldr.test_login()
                    if logged_user:
                        print(f"[✓] Menggunakan sesi akun aktif: @{logged_user}")
                        if s_file != SESSION_FILE:
                            print(f"    (Otomatis terhubung dari: {s_file.parent.name})")
                            save_and_share_session(test_ldr, logged_user)
                        return test_ldr
            except Exception:
                continue

    return None


def parse_target_config() -> dict:
    """Membaca pengaturan target dari input_target.txt."""
    if not CONFIG_FILE.exists():
        return {}

    cfg = {
        "targets": [],
        "tipe_data": "followers",
        "maksimal_data": 100,
        "jeda_detik": 1.5,
        "format": "semua",
    }

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        target_lines = []
        is_reading_targets = False

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if "=" in line:
                k, _, v = line.partition("=")
                key = k.strip().upper()
                val = v.strip()

                if key == "TARGET_AKUN":
                    is_reading_targets = True
                    if val and not val.startswith("#"):
                        target_lines.append(val)
                else:
                    is_reading_targets = False
                    if key == "TIPE_DATA":
                        cfg["tipe_data"] = "following" if "follow" in val.lower() and "ing" in val.lower() else "followers"
                    elif key == "MAKSIMAL_DATA":
                        try:
                            cfg["maksimal_data"] = max(0, int(val))
                        except ValueError:
                            cfg["maksimal_data"] = 100
                    elif key == "JEDA_DETIK":
                        try:
                            cfg["jeda_detik"] = max(0.5, float(val))
                        except ValueError:
                            cfg["jeda_detik"] = 1.5
                    elif key == "FORMAT":
                        val_low = val.lower()
                        if "txt" in val_low and "csv" not in val_low:
                            cfg["format"] = "txt"
                        elif "csv" in val_low and "txt" not in val_low:
                            cfg["format"] = "csv"
                        else:
                            cfg["format"] = "semua"
            elif is_reading_targets:
                if stripped and not stripped.startswith("#"):
                    target_lines.append(stripped)

        clean_targets = []
        for raw in target_lines:
            for item in raw.replace(",", " ").split():
                clean = extract_username(item)
                if clean and clean not in clean_targets:
                    clean_targets.append(clean)

        cfg["targets"] = clean_targets
    except Exception as e:
        print(f"[!] Gagal membaca input_target.txt: {e}")

    return cfg


def prompt_user_target() -> dict:
    """Prompt interaktif jika input_target.txt belum diisi."""
    print("=" * 65)
    print(" PENGATURAN TARGET SCRAPER FOLLOWER INSTAGRAM")
    print("=" * 65)
    print("File 'input_target.txt' belum terisi target.")
    print("Silakan tentukan akun Instagram yang ingin Anda scrape:")

    targets = []
    while not targets:
        raw = input("\nTarget Akun (Username atau link URL Instagram, pisah koma): ").strip()
        for item in raw.replace(",", " ").split():
            c = extract_username(item)
            if c and c not in targets:
                targets.append(c)
        if not targets:
            print("[!] Masukkan minimal 1 target username / link yang valid.")

    print("\nTipe Data:")
    print("1. Followers (Daftar Pengikut) [Default]")
    print("2. Following (Daftar Yang Diikuti)")
    c_tipe = input("Pilih tipe (1/2, default 1): ").strip()
    tipe_data = "following" if c_tipe == "2" else "followers"

    raw_max = input("\nJumlah data yang ingin diambil (0 = SEMUA, default 100): ").strip()
    try:
        maksimal_data = max(0, int(raw_max)) if raw_max else 100
    except ValueError:
        maksimal_data = 100

    raw_jeda = input("Jeda acak antar akun (detik, default 1.5): ").strip()
    try:
        jeda_detik = max(0.5, float(raw_jeda)) if raw_jeda else 1.5
    except ValueError:
        jeda_detik = 1.5

    print("\nFormat Penyimpanan:")
    print("1. Semua (TXT & CSV Excel) [Default]")
    print("2. TXT saja (Hanya username baris demi baris)")
    print("3. CSV saja (Tabel lengkap Excel)")
    c_fmt = input("Pilih format (1/2/3, default 1): ").strip()
    if c_fmt == "2":
        fmt = "txt"
    elif c_fmt == "3":
        fmt = "csv"
    else:
        fmt = "semua"

    simpan = input("\nSimpan pengaturan ini ke 'input_target.txt'? (Y/n, default Y): ").strip().lower()
    if simpan in ("", "y", "ya", "yes"):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(
                    "# Pengaturan Target Scraper Instagram\n"
                    f"TARGET_AKUN={', '.join(targets)}\n"
                    f"TIPE_DATA={tipe_data}\n"
                    f"MAKSIMAL_DATA={maksimal_data}\n"
                    f"JEDA_DETIK={jeda_detik}\n"
                    f"FORMAT={fmt}\n"
                )
            print("[✓] Pengaturan disimpan ke input_target.txt")
        except Exception as e:
            print(f"[!] Gagal menyimpan ke input_target.txt: {e}")

    return {
        "targets": targets,
        "tipe_data": tipe_data,
        "maksimal_data": maksimal_data,
        "jeda_detik": jeda_detik,
        "format": fmt,
    }


def scrape_instagram_connections(loader: instaloader.Instaloader, cfg: dict):
    """Menjalankan proses scraping followers / following menggunakan REST API Instagram."""
    targets = cfg["targets"]
    tipe_data = cfg.get("tipe_data", "followers")
    maksimal_data = cfg.get("maksimal_data", 100)
    jeda_detik = cfg.get("jeda_detik", 1.5)
    fmt = cfg.get("format", "semua")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    label_tipe = "Followers (Pengikut)" if tipe_data == "followers" else "Following (Mengikuti)"
    file_suffix = "followers" if tipe_data == "followers" else "following"

    print("\n" + "=" * 65)
    print(" MEMULAI SCRAPING AKUN INSTAGRAM")
    print("=" * 65)
    print(f"Target Akun   : {len(targets)} akun ({', '.join(targets)})")
    print(f"Tipe Data     : {label_tipe}")
    print(f"Maksimal Data : {'Semua (Tanpa batas)' if maksimal_data == 0 else f'{maksimal_data} per akun'}")
    print(f"Jeda Istirahat: ~{jeda_detik} detik")
    print(f"Format Output : {fmt.upper()}")
    print(f"Folder Output : {OUTPUT_DIR.resolve()}")
    print("=" * 65 + "\n")

    summary = []

    # Siapkan requests.Session yang mewarisi cookies dari Instaloader
    session = requests.Session()
    session.cookies.update(loader.context._session.cookies)

    csrf = ""
    for c in session.cookies:
        if c.name == "csrftoken":
            csrf = c.value
            break

    for idx, target in enumerate(targets, start=1):
        print(f"[{idx}/{len(targets)}] Memproses target: @{target}")

        try:
            profile = instaloader.Profile.from_username(loader.context, target)
        except ProfileNotExistsException:
            print(f"     [x] Profil @{target} tidak ditemukan atau tidak tersedia.\n")
            summary.append({"target": target, "status": "Tidak ditemukan", "count": 0})
            continue
        except Exception as e:
            print(f"     [x] Gagal memuat profil @{target}: {e}\n")
            summary.append({"target": target, "status": f"Gagal: {e}", "count": 0})
            continue

        try:
            total_est = profile.followers if tipe_data == "followers" else profile.followees
            print(f"     [*] Nama Tampilan : {profile.full_name or '-'}")
            print(f"     [*] Total {label_tipe} terdaftar: {total_est:,}")
            if profile.is_private:
                print("     [*] Status: Akun Privat")
        except Exception:
            total_est = 0

        target_id = str(profile.userid)
        headers = {
            "x-ig-app-id": "936619743392459",
            "x-asbd-id": "359341",
            "x-csrftoken": csrf,
            "x-requested-with": "XMLHttpRequest",
            "referer": f"https://www.instagram.com/{profile.username}/",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "accept": "*/*",
            "sec-ch-ua-platform": '"Windows"',
            "sec-ch-ua-mobile": "?0",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
        }

        # Inisialisasi file output
        txt_file = OUTPUT_DIR / f"{target}_{file_suffix}.txt"
        csv_file = OUTPUT_DIR / f"{target}_{file_suffix}.csv"

        txt_fp = None
        csv_fp = None
        csv_writer = None

        if fmt in ("semua", "txt"):
            txt_fp = open(txt_file, "w", encoding="utf-8")
            txt_fp.write(f"# Daftar {label_tipe} untuk Akun @{target}\n")
            txt_fp.write(f"# Waktu Scrape: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            txt_fp.write("#" + "=" * 50 + "\n")

        if fmt in ("semua", "csv"):
            csv_fp = open(csv_file, "w", encoding="utf-8-sig", newline="")
            csv_writer = csv.writer(csv_fp)
            csv_writer.writerow([
                "No",
                "Username",
                "Nama_Lengkap",
                "User_ID",
                "Centang_Biru",
                "Akun_Privat",
                "URL_Profil",
                "URL_Foto_Profil",
            ])

        print(f"     [*] Mengambil daftar {file_suffix} (tekan Ctrl+C kapan saja untuk berhenti dan menyimpan)...")
        count = 0
        max_disp = str(maksimal_data) if maksimal_data > 0 else f"semua ({total_est:,})"
        consecutive_rate_limits = 0
        base_url = f"https://www.instagram.com/api/v1/friendships/{target_id}/{tipe_data}/"
        max_id = None
        is_finished = False

        try:
            while not is_finished:
                params = {"count": 50}
                if tipe_data == "followers":
                    params["search_surface"] = "follow_list_page"
                if max_id:
                    params["max_id"] = str(max_id)

                try:
                    resp = session.get(base_url, headers=headers, params=params, timeout=30)
                except Exception as req_err:
                    print(f"\n     [!] Masalah jaringan saat mengambil data: {req_err}")
                    break

                if resp.status_code == 429:
                    consecutive_rate_limits += 1
                    if consecutive_rate_limits > 2:
                        print("\n     [!] Instagram memberlakukan pembatasan frekuensi (Rate Limit 429).")
                        print(f"     [!] Menyimpan {count:,} data yang telah didapat...")
                        break
                    wait_sec = 25 * consecutive_rate_limits
                    print(f"\n     [!] Terkena rate limit (429). Menunggu jeda pendinginan {wait_sec} detik...")
                    time.sleep(wait_sec)
                    continue

                if resp.status_code != 200:
                    err_msg = ""
                    try:
                        err_msg = resp.json().get("message", "")
                    except Exception:
                        pass
                    if resp.status_code == 400 and "checkpoint" in err_msg.lower():
                        print(f"\n     [!] Akun memerlukan verifikasi checkpoint Instagram.")
                    elif resp.status_code == 403 or "not authorized" in err_msg.lower():
                        print(f"\n     [!] Tidak diizinkan mengakses data target @{target} (Akun Privat / Belum di-follow).")
                    else:
                        print(f"\n     [!] Gagal mengambil {label_tipe} (HTTP {resp.status_code}): {err_msg or resp.reason}")
                    break

                consecutive_rate_limits = 0

                try:
                    data = resp.json()
                except Exception:
                    print(f"\n     [!] Respons server bukan JSON yang valid.")
                    break

                users = data.get("users", [])
                if not users:
                    break

                for u in users:
                    count += 1
                    u_name = u.get("username", "")
                    if not u_name:
                        continue
                    f_name = u.get("full_name", "") or ""
                    u_id = str(u.get("pk") or u.get("id") or "")
                    is_verif = "Ya" if u.get("is_verified") else "Tidak"
                    is_priv = "Ya" if u.get("is_private") else "Tidak"
                    p_url = f"https://www.instagram.com/{u_name}/"
                    pic_url = u.get("profile_pic_url", "") or ""

                    # Tulis ke file TXT & CSV secara instan (auto flush)
                    if txt_fp:
                        txt_fp.write(f"{u_name}\n")
                        txt_fp.flush()

                    if csv_writer:
                        csv_writer.writerow([
                            count,
                            u_name,
                            f_name,
                            u_id,
                            is_verif,
                            is_priv,
                            p_url,
                            pic_url,
                        ])
                        csv_fp.flush()

                    # Cetak log per follower
                    verif_badge = " [✓]" if is_verif == "Ya" else ""
                    print(f"     [{count}/{max_disp}] @{u_name}{verif_badge} ({f_name[:30]})")

                    # Berhenti jika batas maksimal tercapai
                    if 0 < maksimal_data <= count:
                        print(f"     [✓] Selesai: Telah mencapai batas target {maksimal_data} data.")
                        is_finished = True
                        break

                if is_finished:
                    break

                max_id = data.get("next_max_id")
                if not max_id:
                    break

                sleep_time = random.uniform(max(0.5, jeda_detik * 0.8), max(1.0, jeda_detik * 1.4))
                time.sleep(sleep_time)

        except KeyboardInterrupt:
            print(f"\n     [!] Dihentikan oleh pengguna (Ctrl+C). Menyimpan {count} data yang telah terkumpul...")

        except Exception as e:
            print(f"\n     [!] Terjadi kendala saat iterasi data: {e}")
            print(f"         Menyimpan {count} data yang berhasil didapatkan...")

        finally:
            if txt_fp:
                txt_fp.close()
            if csv_fp:
                csv_fp.close()

        print(f"     [✓] Sukses mengumpulkan {count:,} {file_suffix} untuk @{target}!")
        if fmt in ("semua", "txt"):
            print(f"         -> TXT : {txt_file.name}")
        if fmt in ("semua", "csv"):
            print(f"         -> CSV : {csv_file.name}")
        print()

        summary.append({
            "target": target,
            "status": "Sukses" if count > 0 else "Selesai",
            "count": count,
            "txt": txt_file.name if fmt in ("semua", "txt") else None,
            "csv": csv_file.name if fmt in ("semua", "csv") else None,
        })

    # Cetak ringkasan akhir
    print("=" * 65)
    print(" RINGKASAN HASIL SCRAPING")
    print("=" * 65)
    for s in summary:
        print(f"- @{s['target']:<20} : {s['status']} ({s['count']:,} data)")
        if s.get("txt"):
            print(f"    File TXT: {OUTPUT_DIR / s['txt']}")
        if s.get("csv"):
            print(f"    File CSV: {OUTPUT_DIR / s['csv']}")
    print("=" * 65)
    print("[✓] Seluruh proses scraping selesai!\n")


def main():
    parser = argparse.ArgumentParser(description="Instagram Follower & Following Scraper")
    parser.add_argument("--login", action="store_true", help="Jalankan autentikasi login Instagram")
    args = parser.parse_args()

    ensure_cookie_template()

    # 1. Jika argumen --login diberikan
    if args.login:
        success = login_interactive()
        if success:
            print("\n[✓] Autentikasi berhasil disiapkan!")
            print("    Sekarang Anda dapat menjalankan 'JALANKAN_SCRAPER.bat' untuk mulai scraping.")
        return

    # 2. Cek apakah ada sesi login yang valid
    loader = get_authenticated_loader()
    if not loader or not loader.context.is_logged_in:
        print("\n" + "=" * 65)
        print(" [!] AUTENTIKASI DIPERLUKAN")
        print("=" * 65)
        print("Instagram tidak mengizinkan tamu tanpa login untuk melihat daftar follower.")
        print("Anda perlu menghubungkan akun Instagram Anda terlebih dahulu.\n")

        cookie_text = ""
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                cookie_text = f.read().strip()
        has_cookies = cookie_text and not all(
            line.strip().startswith("#") or not line.strip() for line in cookie_text.splitlines()
        )

        if has_cookies:
            print("[*] Ditemukan cookies di 'input_cookie.txt'. Mencoba validasi otomatis...")
            cookies = parse_cookies_from_text(cookie_text)
            is_valid, detected_user = verify_and_get_username(cookies)
            if is_valid:
                username = detected_user or "user"
                ldr = instaloader.Instaloader(sleep=False)
                for domain in [".instagram.com", "instagram.com"]:
                    for k, v in cookies.items():
                        ldr.context._session.cookies.set(k, v, domain=domain, path="/")
                ldr.context.username = username
                save_and_share_session(ldr, username)
                print(f"[✓] Berhasil login otomatis menggunakan input_cookie.txt (@{username})!\n")
                loader = ldr

        if not loader or not loader.context.is_logged_in:
            tanya = input("Apakah Anda ingin login sekarang? (Y/n, default Y): ").strip().lower()
            if tanya in ("", "y", "ya", "yes"):
                login_ok = login_interactive()
                if login_ok:
                    loader = get_authenticated_loader()
                else:
                    print("\n[x] Login dibatalkan atau gagal. Silakan coba lagi nanti.")
                    return
            else:
                print("\n[x] Proses dibatalkan karena Instagram mewajibkan login untuk membaca follower.")
                print("    Silakan klik 2x 'LOGIN_AKUN.bat' jika sudah siap.")
                return

    # 3. Baca konfigurasi target
    cfg = parse_target_config()
    if not cfg or not cfg.get("targets"):
        cfg = prompt_user_target()

    if not cfg or not cfg.get("targets"):
        print("\n[x] Tidak ada target yang diproses. Program selesai.")
        return

    # 4. Jalankan scraping
    scrape_instagram_connections(loader, cfg)


if __name__ == "__main__":
    main()
