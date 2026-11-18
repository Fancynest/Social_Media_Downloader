"""
Instagram Unfollowers & Follback Tracker
=========================================
Menganalisis akun Instagram Anda untuk mendeteksi:
1. Siapa yang Anda follow tapi TIDAK FOLLOW BALIK (Unfollow / Not Following Back).
2. Fans (Akun yang follow Anda, tapi tidak Anda follow balik).
3. Saling follow (Mutual).
4. Riwayat Unfollow: Siapa yang baru saja unfollow Anda sejak scan terakhir!
"""

import os
import re
import sys
import csv
import json
import time
import random
import getpass
import argparse
from pathlib import Path
from datetime import datetime
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

# Path konfigurasi file & folder
BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_DIR = BASE_DIR / "Hasil_Analisis"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
SESSION_FILE = BASE_DIR / "session.dat"
USER_FILE = BASE_DIR / "session_user.txt"
HISTORY_FILE = BASE_DIR / "riwayat_followers.json"


def ensure_cookie_template():
    """Pastikan file input_cookie.txt selalu tersedia dengan petunjuk."""
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
    """Mengekstrak username bersih dari teks atau URL Instagram."""
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
    """Mengekstrak cookies dari format Netscape (.txt) atau header HTTP."""
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
    """Memverifikasi cookies ke server Instagram dan mengambil username akun."""
    session = requests.Session()
    for domain in [".instagram.com", "instagram.com", "www.instagram.com"]:
        for k, v in cookies.items():
            session.cookies.set(k, v, domain=domain, path="/")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
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
            return True, None

        if resp.status_code == 200 and uid:
            return True, None

    except Exception as e:
        print(f"     [!] Gagal verifikasi cookies: {e}")

    return False, None


def save_and_share_session(loader: instaloader.Instaloader, username: str):
    """Menyimpan sesi ke folder lokal dan menyinkronkan ke modul Instagram lainnya."""
    SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
    loader.save_session_to_file(str(SESSION_FILE))
    with open(USER_FILE, "w", encoding="utf-8") as f:
        f.write(username)

    sync_targets = [
        BASE_DIR.parent,
        BASE_DIR.parent / "1_Instagram_Followers",
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
    """Alur login interaktif melalui Cookies Notepad atau Username & Password."""
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


def get_authenticated_loader() -> Tuple[Optional[instaloader.Instaloader], Optional[str]]:
    """Mencari dan memuat sesi login aktif dari berbagai folder modul Instagram."""
    search_locations = [
        (SESSION_FILE, USER_FILE),
        (BASE_DIR.parent / "session.dat", BASE_DIR.parent / "session_user.txt"),
        (BASE_DIR.parent / "1_Instagram_Followers" / "session.dat",
         BASE_DIR.parent / "1_Instagram_Followers" / "session_user.txt"),
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
                            print(f"    (Terhubung otomatis dari: {s_file.parent.name})")
                            save_and_share_session(test_ldr, logged_user)
                        return test_ldr, logged_user
            except Exception:
                continue

    return None, None


def fetch_account_connections(loader: instaloader.Instaloader, profile: instaloader.Profile, fetch_type: str) -> Dict[str, dict]:
    """
    Mengambil data Following atau Followers menggunakan Instagram Web API langsung (REST endpoint).
    Sangat stabil, cepat, dan tidak terpengaruh deprecation GraphQL query_hash.
    fetch_type: 'following' atau 'followers'
    """
    results = {}
    label = "Following (Yang Anda Ikuti)" if fetch_type == "following" else "Followers (Pengikut Anda)"
    total_est = getattr(profile, "followees" if fetch_type == "following" else "followers", 0) or 0

    print(f"\n[*] Mengambil daftar {label} (Total terdaftar: ~{total_est:,})...")

    # Siapkan requests.Session yang mewarisi cookies dari Instaloader
    session = requests.Session()
    session.cookies.update(loader.context._session.cookies)

    csrf = ""
    for c in session.cookies:
        if c.name == "csrftoken":
            csrf = c.value
            break

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

    base_url = f"https://www.instagram.com/api/v1/friendships/{target_id}/{fetch_type}/"
    max_id = None
    count = 0
    consecutive_rate_limits = 0

    try:
        while True:
            params = {"count": 50}
            if fetch_type == "followers":
                params["search_surface"] = "follow_list_page"
            if max_id:
                params["max_id"] = str(max_id)

            try:
                resp = session.get(base_url, headers=headers, params=params, timeout=30)
            except Exception as req_err:
                print(f"     [!] Masalah jaringan saat mengambil data: {req_err}")
                break

            if resp.status_code == 429:
                consecutive_rate_limits += 1
                if consecutive_rate_limits > 2:
                    print("\n     [!] Instagram memberlakukan pembatasan frekuensi (Rate Limit 429).")
                    print(f"     [!] Menggunakan {len(results):,} data yang berhasil didapat sejauh ini...")
                    break
                wait_sec = 20 * consecutive_rate_limits
                print(f"\n     [!] Terkena rate limit sementara (429). Menunggu jeda {wait_sec} detik...")
                time.sleep(wait_sec)
                continue

            if resp.status_code != 200:
                err_msg = ""
                try:
                    err_msg = resp.json().get("message", "")
                except Exception:
                    pass
                print(f"\n     [!] Gagal mengambil {label} (HTTP {resp.status_code}): {err_msg or resp.reason}")
                break

            consecutive_rate_limits = 0

            try:
                data = resp.json()
            except Exception:
                print(f"\n     [!] Respons server bukan format JSON yang valid.")
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

                results[u_name.lower()] = {
                    "username": u_name,
                    "full_name": f_name,
                    "user_id": u_id,
                    "is_verified": is_verif,
                    "is_private": is_priv,
                    "profile_url": p_url,
                    "pic_url": pic_url,
                }

            if count % 50 == 0 or (total_est > 0 and count >= total_est):
                print(f"     -> Terbaca: {len(results):,} / ~{total_est:,} akun...")

            max_id = data.get("next_max_id")
            if not max_id:
                break

            time.sleep(random.uniform(1.2, 2.2))

    except KeyboardInterrupt:
        print(f"\n     [!] Dihentikan pengguna (Ctrl+C). Menggunakan {len(results):,} data yang terkumpul...")
    except Exception as e:
        print(f"\n     [!] Peringatan saat mengambil data: {e}. Menggunakan {len(results):,} data yang telah didapat.")

    print(f"     [✓] Sukses mengambil {len(results):,} {label}!")
    return results


def export_result_files(target_username: str, data_list: List[dict], category_name: str, file_prefix: str):
    """Menyimpan hasil ke format TXT dan CSV (Excel UTF-8 BOM)."""
    if not data_list:
        return

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    txt_path = OUTPUT_DIR / f"{target_username}_{file_prefix}.txt"
    csv_path = OUTPUT_DIR / f"{target_username}_{file_prefix}.csv"

    # 1. Simpan TXT (Daftar username bersih)
    with open(txt_path, "w", encoding="utf-8") as tf:
        tf.write(f"# {category_name} untuk Akun @{target_username}\n")
        tf.write(f"# Total: {len(data_list):,} akun\n")
        tf.write(f"# Waktu Analisis: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        tf.write("#" + "=" * 55 + "\n")
        for item in data_list:
            tf.write(f"{item['username']}\n")

    # 2. Simpan CSV (Tabel Excel rapi)
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as cf:
        writer = csv.writer(cf)
        writer.writerow([
            "No",
            "Username",
            "Nama_Lengkap",
            "User_ID",
            "Centang_Biru",
            "Akun_Privat",
            "URL_Profil",
            "Kategori",
        ])
        for idx, item in enumerate(data_list, start=1):
            writer.writerow([
                idx,
                item["username"],
                item.get("full_name", ""),
                item.get("user_id", ""),
                item.get("is_verified", "Tidak"),
                item.get("is_private", "Tidak"),
                item.get("profile_url", f"https://www.instagram.com/{item['username']}/"),
                category_name,
            ])


def analyze_unfollowers(target_username: str, following_dict: Dict[str, dict], followers_dict: Dict[str, dict]):
    """Membandingkan data Following dan Followers serta riwayat scan sebelumnya."""
    print("\n" + "=" * 65)
    print(f" MEMPROSES ANALISIS HUBUNGAN AKUN @{target_username}")
    print("=" * 65)

    following_set = set(following_dict.keys())
    followers_set = set(followers_dict.keys())

    # 1. Tidak Follow Balik (Anda Follow, Tapi Mereka TIDAK Follow Anda)
    not_following_back_keys = sorted(list(following_set - followers_set))
    not_following_back_list = [following_dict[k] for k in not_following_back_keys]

    # 2. Fans (Mereka Follow Anda, Tapi Anda Tidak Follow Mereka)
    fans_keys = sorted(list(followers_set - following_set))
    fans_list = [followers_dict[k] for k in fans_keys]

    # 3. Saling Follow (Mutual)
    mutual_keys = sorted(list(following_set & followers_set))
    mutual_list = [following_dict[k] for k in mutual_keys]

    # 4. Riwayat Unfollow dari snapshot sebelumnya
    prev_followers = set()
    prev_scan_time = None
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as hf:
                history_data = json.load(hf)
                if history_data.get("target_username") == target_username.lower():
                    prev_followers = set(history_data.get("followers", []))
                    prev_scan_time = history_data.get("timestamp")
        except Exception:
            pass

    unfollowed_since_last_scan = []
    new_followers_since_last_scan = []

    if prev_followers:
        lost_keys = sorted(list(prev_followers - followers_set))
        unfollowed_since_last_scan = [{"username": u} for u in lost_keys]

        gained_keys = sorted(list(followers_set - prev_followers))
        new_followers_since_last_scan = [followers_dict[u] for u in gained_keys if u in followers_dict]

    # Simpan snapshot saat ini ke riwayat
    new_history_payload = {
        "target_username": target_username.lower(),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "followers": sorted(list(followers_set)),
        "following": sorted(list(following_set)),
    }
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as hf:
            json.dump(new_history_payload, hf, indent=2)
    except Exception as e:
        print(f"[!] Gagal memperbarui riwayat: {e}")

    # Export seluruh hasil ke folder Hasil_Analisis/
    export_result_files(target_username, not_following_back_list, "Tidak Follow Balik", "tidak_follow_balik")
    export_result_files(target_username, fans_list, "Fans (Tidak Anda Follback)", "fans_tidak_di_follback")
    export_result_files(target_username, mutual_list, "Saling Follow (Mutual)", "saling_follow_mutual")
    if unfollowed_since_last_scan:
        export_result_files(target_username, unfollowed_since_last_scan, "Baru Unfollow Sejak Scan Terakhir", "riwayat_unfollow_terbaru")

    # Cetak Papan Skor Ringkasan Rapi
    print("\n" + "=" * 65)
    print(f" PAPAN SKOR HASIL ANALISIS AKUN: @{target_username}")
    print("=" * 65)
    print(f" Total Following (Yang Anda Ikuti) : {len(following_dict):,} akun")
    print(f" Total Followers (Pengikut Anda)   : {len(followers_dict):,} akun")
    print("-" * 65)
    print(f" [!] TIDAK FOLLOW BALIK (UNFOLLOW) : {len(not_following_back_list):,} akun")
    print(f"     -> File: {target_username}_tidak_follow_balik.csv & .txt")
    print(f" [+] FANS (Tidak Anda Follback)    : {len(fans_list):,} akun")
    print(f"     -> File: {target_username}_fans_tidak_di_follback.csv & .txt")
    print(f" [✓] SALING FOLLOW (MUTUAL)        : {len(mutual_list):,} akun")
    print(f"     -> File: {target_username}_saling_follow_mutual.csv & .txt")
    print("-" * 65)

    if prev_followers and prev_scan_time:
        print(f" [*] RIWAYAT DETEKSI (Dibandingkan Scan Terakhir: {prev_scan_time}):")
        print(f"     - {len(unfollowed_since_last_scan)} akun telah meng-UNFOLLOW Anda!")
        if unfollowed_since_last_scan:
            print(f"       File: {target_username}_riwayat_unfollow_terbaru.csv & .txt")
            contoh = [f"@{x['username']}" for x in unfollowed_since_last_scan[:5]]
            print(f"       Contoh akun yang unfollow: {', '.join(contoh)}{'...' if len(unfollowed_since_last_scan) > 5 else ''}")
        print(f"     - {len(new_followers_since_last_scan)} akun follower baru.")
    else:
        print(" [*] Catatan Riwayat: Snapshot awal berhasil disimpan.")
        print("     Pada pengecekan berikutnya, tool ini akan otomatis memberitahu Anda")
        print("     siapa saja akun yang BARU meng-unfollow Anda!")

    print("=" * 65)
    print(f"[✓] Semua data tersimpan rapi di: {OUTPUT_DIR.resolve()}\n")


def main():
    parser = argparse.ArgumentParser(description="Instagram Unfollowers & Follback Tracker")
    parser.add_argument("--login", action="store_true", help="Jalankan autentikasi login akun Instagram")
    parser.add_argument("--target", type=str, default="", help="Username Instagram target yang ingin dicek")
    args = parser.parse_args()

    ensure_cookie_template()

    # 1. Jika pengguna memanggil dengan flag --login
    if args.login:
        success = login_interactive()
        if success:
            print("\n[✓] Autentikasi berhasil disiapkan!")
            print("    Sekarang Anda dapat menjalankan 'CEK_UNFOLLOWERS.bat'.")
        return

    # 2. Cek apakah ada sesi login aktif
    loader, logged_in_username = get_authenticated_loader()
    if not loader or not logged_in_username:
        print("\n" + "=" * 65)
        print(" [!] AUTENTIKASI DIPERLUKAN")
        print("=" * 65)
        print("Untuk menganalisis akun dan mendeteksi unfollowers, Anda perlu login.")
        print("Alat ini berjalan 100% lokal di komputer Anda dan aman.\n")

        # Cek jika ada cookies di input_cookie.txt
        cookie_text = ""
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                cookie_text = f.read().strip()
        has_cookies = cookie_text and not all(
            line.strip().startswith("#") or not line.strip() for line in cookie_text.splitlines()
        )

        if has_cookies:
            print("[*] Ditemukan cookies di 'input_cookie.txt'. Memvalidasi otomatis...")
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
                logged_in_username = username

        if not loader or not logged_in_username:
            tanya = input("Apakah Anda ingin login sekarang? (Y/n, default Y): ").strip().lower()
            if tanya in ("", "y", "ya", "yes"):
                login_ok = login_interactive()
                if login_ok:
                    loader, logged_in_username = get_authenticated_loader()
                else:
                    print("\n[x] Login dibatalkan atau gagal.")
                    return
            else:
                print("\n[x] Proses dibatalkan. Silakan klik 2x 'LOGIN_AKUN.bat' jika sudah siap.")
                return

    # 3. Tentukan target akun yang ingin dianalisis
    target_user = args.target.strip()
    if not target_user:
        print(f"\nAkun login yang aktif saat ini: @{logged_in_username}")
        tanya_akun = input(f"Analisis akun sendiri (@{logged_in_username})? (Y/n, atau ketik username lain): ").strip()
        if tanya_akun.lower() in ("", "y", "ya", "yes"):
            target_user = logged_in_username
        else:
            cleaned = extract_username(tanya_akun)
            target_user = cleaned if cleaned else logged_in_username

    print(f"\n[*] Memuat data profil Instagram: @{target_user}...")
    try:
        profile = instaloader.Profile.from_username(loader.context, target_user)
    except ProfileNotExistsException:
        print(f"[x] Profil @{target_user} tidak ditemukan.")
        return
    except Exception as e:
        print(f"[x] Gagal mengakses profil @{target_user}: {e}")
        return

    # 4. Ambil Following & Followers
    following_data = fetch_account_connections(loader, profile, "following")
    followers_data = fetch_account_connections(loader, profile, "followers")

    expected_followers = getattr(profile, "followers", 0) or 0
    expected_following = getattr(profile, "followees", 0) or 0

    if not followers_data and expected_followers > 0:
        print("\n" + "=" * 65)
        print(" [!] PERINGATAN: DAFTAR FOLLOWERS BELUM DAPAT DIAMBIL")
        print("=" * 65)
        print(f" Instagram membatasi akses followers (Rate Limit 429) untuk @{target_user}.")
        print(" Untuk mencegah kesalahan analisis (false positive), proses perbandingan ditunda.")
        print(" Silakan beri jeda 15-30 menit lalu jalankan kembali CEK_UNFOLLOWERS.bat.")
        print("=" * 65)
        return

    if not following_data and expected_following > 0:
        print("\n" + "=" * 65)
        print(" [!] PERINGATAN: DAFTAR FOLLOWING BELUM DAPAT DIAMBIL")
        print("=" * 65)
        print(f" Instagram membatasi akses following (Rate Limit 429) untuk @{target_user}.")
        print(" Untuk mencegah kesalahan analisis (false positive), proses perbandingan ditunda.")
        print(" Silakan beri jeda 15-30 menit lalu jalankan kembali CEK_UNFOLLOWERS.bat.")
        print("=" * 65)
        return

    if not following_data and not followers_data:
        print("\n[x] Tidak ada data yang berhasil diambil. Program selesai.")
        return

    # 5. Lakukan komparasi & analisis
    analyze_unfollowers(target_user, following_data, followers_data)


if __name__ == "__main__":
    main()
