# -*- coding: utf-8 -*-
import os
import sys
import re
import time
import random
import getpass
import argparse
from pathlib import Path
from typing import Optional, Tuple

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import requests
import instaloader
from instaloader.exceptions import (
    ProfileNotExistsException,
    PrivateProfileNotFollowedException,
    LoginRequiredException,
    TooManyRequestsException,
    BadCredentialsException,
    TwoFactorAuthRequiredException,
)


def _patch_instaloader():
    """
    1. Arahkan query doc_id GraphQL ke /api/graphql agar tidak terkena 400 feedback_required / 302.
    2. Fallback Profile.from_username dengan sesi login untuk akun dengan konten restricted / sensitif / batas usia.
    """
    orig_doc_id = instaloader.InstaloaderContext.doc_id_graphql_query

    def patched_doc_id(self, doc_id: str, variables: dict, referer: Optional[str] = None, web_api: bool = True):
        return orig_doc_id(self, doc_id, variables, referer=referer, web_api=True)

    instaloader.InstaloaderContext.doc_id_graphql_query = patched_doc_id

    orig_from_username = instaloader.Profile.from_username

    def patched_from_username(cls, context, username: str):
        try:
            return orig_from_username(context, username)
        except ProfileNotExistsException:
            # Jika Instaloader anonymous request gagal (karena akun restricted/sensitif/age-gated),
            # buka halaman menggunakan sesi login aktif pengguna.
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
                return cls(context, node)

            raise ProfileNotExistsException(f"Profile {username} does not exist.")

    instaloader.Profile.from_username = classmethod(patched_from_username)


_patch_instaloader()

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "input_target.txt"
COOKIE_FILE = BASE_DIR / "input_cookie.txt"
SESSION_FILE = BASE_DIR / "session.dat"
USER_FILE = BASE_DIR / "session_user.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"


def parse_cookies_from_text(text: str) -> dict:
    cookies = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) >= 7:
            cookies[parts[5].strip()] = parts[6].strip()
        elif "=" in line:
            for item in line.split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    cookies[k.strip()] = v.strip().strip('"').strip("'")
        elif len(line) > 15 and ("%3A" in line or len(line) > 25):
            cookies["sessionid"] = line.strip().strip('"').strip("'")
    return cookies


def extract_username(val: str) -> str:
    s = val.strip()
    if not s or s.startswith("#"):
        return ""
    s = s.rstrip("/")
    if "instagram.com/" in s:
        if s.startswith("#"):
            return ""
        parts = s.split("instagram.com/")[1].split("?")[0].split("/")
        s = parts[0] if parts else s
    s = s.lstrip("@").strip()
    if not s or s.startswith("#"):
        return ""
    return s


def read_config():
    if not CONFIG_FILE.exists():
        return None

    targets = []
    keywords = []
    hashtags = []
    max_posts = 50
    save_caption = False
    current_key = None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8-sig") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    current_key = k.strip().upper()
                    val = v.strip()
                else:
                    val = line

                if current_key == "TARGET_AKUN":
                    tokens = [t.strip() for t in val.replace(",", " ").split() if t.strip()]
                    skip_next = False
                    for item in tokens:
                        if item == "#":
                            skip_next = True
                            continue
                        if skip_next:
                            skip_next = False
                            continue
                        if item.startswith("#"):
                            continue
                        cleaned = extract_username(item)
                        if cleaned and not cleaned.startswith("#") and cleaned not in targets:
                            targets.append(cleaned)
                elif current_key == "KEYWORDS":
                    for item in val.split(","):
                        k_clean = item.strip().lower()
                        if k_clean and k_clean not in keywords:
                            keywords.append(k_clean)
                elif current_key == "HASHTAGS":
                    for item in val.split(","):
                        h_clean = item.strip().lower()
                        if h_clean:
                            tag = h_clean if h_clean.startswith("#") else f"#{h_clean}"
                            if tag not in hashtags:
                                hashtags.append(tag)
                elif current_key == "MAKSIMAL_POST":
                    try:
                        max_posts = int(val)
                    except ValueError:
                        pass
                elif current_key == "SIMPAN_CAPTION":
                    save_caption = val.strip().lower() in ("ya", "yes", "true", "1", "y")
    except Exception as e:
        print(f"[!] Gagal membaca {CONFIG_FILE.name}: {e}")

    has_filter = bool(keywords or hashtags)
    return {
        "targets": targets,
        "keywords": keywords,
        "hashtags": hashtags,
        "max_posts": max_posts,
        "save_caption": save_caption,
    } if (targets and has_filter) else None


def prompt_user_input():
    print("[*] Konfigurasi pencarian:\n")
    while True:
        raw_target = input("  -> Akun Target (bisa 1 atau banyak akun, pisahkan koma/spasi): ").strip()
        targets = []
        tokens = [t.strip() for t in raw_target.replace(",", " ").split() if t.strip()]
        skip_next = False
        for item in tokens:
            if item == "#":
                skip_next = True
                continue
            if skip_next:
                skip_next = False
                continue
            if item.startswith("#"):
                continue
            cleaned = extract_username(item)
            if cleaned and not cleaned.startswith("#") and cleaned not in targets:
                targets.append(cleaned)
        if targets:
            break
        print("     [!] Masukkan minimal satu username / link akun yang valid.")

    while True:
        raw_kw = input("  -> Kata Kunci / Keywords (pisahkan koma): ").strip()
        keywords = [k.strip().lower() for k in raw_kw.split(",") if k.strip()]
        raw_ht = input("  -> Tagar / Hashtags (opsional, pisahkan koma, contoh #tag1, #tag2): ").strip()
        hashtags = []
        for item in raw_ht.split(","):
            h = item.strip().lower()
            if h:
                tag = h if h.startswith("#") else f"#{h}"
                if tag not in hashtags:
                    hashtags.append(tag)

        if keywords or hashtags:
            break
        print("     [!] Masukkan minimal satu kata kunci atau tagar.")

    raw_max = input("  -> Maksimal postingan per akun (Enter untuk default 50, atau 0 untuk semua): ").strip()
    try:
        max_posts = int(raw_max) if raw_max else 50
    except ValueError:
        max_posts = 50

    raw_caption = input("  -> Simpan teks caption ke file .txt? (y/N, default N): ").strip().lower()
    save_caption = raw_caption in ("y", "ya", "yes", "true", "1")

    save = input("\n  -> Simpan ke input_target.txt? (Y/n, default Y): ").strip().lower()
    if save in ("", "y", "ya", "yes"):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(
                    "# Pengaturan Target Download Instagram\n"
                    f"TARGET_AKUN={', '.join(targets)}\n"
                    f"KEYWORDS={', '.join(keywords)}\n"
                    f"HASHTAGS={', '.join(hashtags)}\n"
                    f"MAKSIMAL_POST={max_posts}\n"
                    f"SIMPAN_CAPTION={'ya' if save_caption else 'tidak'}\n"
                )
            print("     [✓] Konfigurasi disimpan ke input_target.txt")
        except Exception as e:
            print(f"     [!] Gagal menyimpan konfigurasi: {e}")

    return {
        "targets": targets,
        "keywords": keywords,
        "hashtags": hashtags,
        "max_posts": max_posts,
        "save_caption": save_caption,
    }


def verify_and_get_username(cookies: dict) -> Tuple[bool, Optional[str]]:
    """
    Memverifikasi validitas cookies ke Instagram web dan mendeteksi username akun.
    Mengembalikan (is_valid, username).
    """
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

        # 1. Cari username dari PolarisViewer (struktur JSON internal Instagram web)
        idx = resp.text.find('["PolarisViewer"')
        if idx != -1:
            snippet = resp.text[idx : idx + 4000]
            m = re.search(r'"username":"([^"]+)"', snippet)
            if m:
                return True, m.group(1)

        # 2. Cari dari payload viewer
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
        print(f"     [!] Koneksi verifikasi: {e}")

    return False, None


def login_interactive():
    print("=" * 60)
    print(" AUTENTIKASI AKUN INSTAGRAM (COOKIE / SESI)")
    print("=" * 60)
    print("1. Melalui Notepad 'input_cookie.txt' (Ekstensi 'Get cookies.txt' / sessionid)")
    print("2. Login langsung (Username & Password)\n")

    choice = input("Pilih metode (1/2, default 1): ").strip()
    if choice != "2":
        cookie_text = ""
        if COOKIE_FILE.exists():
            with open(COOKIE_FILE, "r", encoding="utf-8", errors="ignore") as f:
                cookie_text = f.read().strip()

        # Jika masih kosong atau hanya komentar, otomatis buka Notepad
        is_empty = not cookie_text or all(line.strip().startswith("#") or not line.strip() for line in cookie_text.splitlines())
        if is_empty:
            print("[*] Membuka Notepad 'input_cookie.txt'...")
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
            return

        print("\n[*] Memverifikasi cookies ke server Instagram...")
        is_valid, detected_user = verify_and_get_username(cookies)

        if not is_valid:
            print("\n[x] Cookies tidak valid atau sesi browser telah kedaluwarsa.")
            print("    Silakan buka instagram.com di browser, pastikan akun sudah login,")
            print("    lalu ekspor ulang cookies dan paste ke input_cookie.txt.")
            return

        username = detected_user
        if not username:
            uid = cookies.get("ds_user_id", "")
            print(f"\n[✓] Cookies valid terverifikasi (User ID: {uid})!")
            raw_u = input("Masukkan username akun Instagram Anda untuk melengkapi sesi: ").strip()
            username = extract_username(raw_u) or f"user_{uid}"

        loader = instaloader.Instaloader()
        for domain in [".instagram.com", "instagram.com"]:
            for k, v in cookies.items():
                loader.context._session.cookies.set(k, v, domain=domain, path="/")
        loader.context.username = username

        try:
            loader.save_session_to_file(str(SESSION_FILE))
            with open(USER_FILE, "w", encoding="utf-8") as f:
                f.write(username)

            # Bagikan sesi ke folder lain agar dapat dipakai bersama
            shared_dirs = [
                BASE_DIR.parent,
                BASE_DIR.parent / "2_Unduh_Banyak_Link",
            ]
            for s_dir in shared_dirs:
                if s_dir.exists():
                    try:
                        loader.save_session_to_file(str(s_dir / "session.dat"))
                        with open(s_dir / "session_user.txt", "w", encoding="utf-8") as pf:
                            pf.write(username)
                    except Exception:
                        pass

            print(f"\n[✓] BERHASIL LOGIN sebagai @{username}!")
            print(f"[✓] Sesi login tersimpan pada: {SESSION_FILE.name}")
            print("    Akun ini sekarang aktif untuk membuka postingan restricted & privat.")
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
        with open(USER_FILE, "w", encoding="utf-8") as f:
            f.write(username)
        print(f"[✓] Berhasil login sebagai @{username}. Sesi disimpan.")
    except TwoFactorAuthRequiredException:
        code = input("Kode 2FA: ").strip()
        try:
            loader.two_factor_login(code)
            loader.save_session_to_file(str(SESSION_FILE))
            with open(USER_FILE, "w", encoding="utf-8") as f:
                f.write(username)
            print("[✓] Login 2FA berhasil.")
        except Exception as e:
            print(f"[x] Verifikasi 2FA gagal: {e}")
    except BadCredentialsException:
        print("[x] Username atau password salah.")
    except Exception as e:
        if "Checkpoint required" in str(e):
            print("[!] Akun terkena checkpoint. Buka aplikasi Instagram di HP lalu pilih 'Ini Saya'.")
        else:
            print(f"[x] Gagal login: {e}")


def get_instaloader_instance(save_caption: bool = False):
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

    session_locations = [
        (SESSION_FILE, USER_FILE),
        (BASE_DIR.parent / "session.dat", BASE_DIR.parent / "session_user.txt"),
    ]
    for s_file, u_file in session_locations:
        if s_file.exists() and u_file.exists():
            try:
                with open(u_file, "r", encoding="utf-8") as f:
                    saved_user = f.read().strip()
                if saved_user:
                    loader.load_session_from_file(saved_user, str(s_file))
                    print(f"[+] Menggunakan sesi login akun: @{saved_user}")
                    return loader
            except Exception as e:
                print(f"[!] Sesi tersimpan pada {s_file.name} gagal dimuat ({e}).")

    print("[+] Berjalan dalam Mode Tamu (Tanpa login)")
    return loader


def main():
    parser = argparse.ArgumentParser(description="Instagram Filter Downloader")
    parser.add_argument("--login", action="store_true", help="Jalankan autentikasi login Instagram")
    args = parser.parse_args()

    if args.login:
        login_interactive()
        input("\nTekan Enter untuk keluar...")
        return

    print("=" * 60)
    print(" INSTAGRAM DOWNLOADER - FILTER KEYWORD & HASHTAG (BATCH)")
    print("=" * 60)

    config = read_config()
    if config:
        print(f"[*] Ditemukan {len(config['targets'])} akun target di input_target.txt:")
        for t in config['targets']:
            print(f"    - @{t}")
        if config['keywords']:
            print(f"[*] Kata Kunci    : {', '.join(config['keywords'])}")
        if config['hashtags']:
            print(f"[*] Tagar/Hashtags: {', '.join(config['hashtags'])}")
        print(f"[*] Batas Per Akun: {config['max_posts'] if config['max_posts'] > 0 else 'Semua postingan'}")
        print(f"[*] Simpan Caption: {'Ya (.txt)' if config.get('save_caption') else 'Tidak (Hanya Foto/Video)'}")
        pilihan = input("\nGunakan pengaturan ini? (Y/n / ketik 'b' untuk input baru): ").strip().lower()
        if pilihan in ("n", "b", "no", "baru"):
            config = prompt_user_input()
    else:
        config = prompt_user_input()

    targets = config["targets"]
    keywords = config["keywords"]
    hashtags = config["hashtags"]
    max_posts = config["max_posts"]
    save_caption = config.get("save_caption", False)

    loader = get_instaloader_instance(save_caption=save_caption)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_accounts = len(targets)
    global_scanned = 0
    global_matched = 0
    account_summary = []

    for acc_idx, target in enumerate(targets, 1):
        if not target or target.startswith("#"):
            continue

        print("\n" + "=" * 60)
        print(f" [{acc_idx}/{total_accounts}] MEMPROSES TARGET: @{target}")
        print("=" * 60)

        out_dir = OUTPUT_DIR / target
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            profile = instaloader.Profile.from_username(loader.context, target)
        except ProfileNotExistsException:
            print(f"[x] Akun @{target} tidak ditemukan. Melewati ke target berikutnya...")
            account_summary.append({"account": target, "scanned": 0, "matched": 0, "status": "Tidak ditemukan"})
            continue
        except LoginRequiredException:
            print(f"[x] Akun @{target} memerlukan login. Jalankan LOGIN_AKUN.bat.")
            account_summary.append({"account": target, "scanned": 0, "matched": 0, "status": "Perlu login"})
            continue
        except Exception as e:
            print(f"[x] Gagal mengakses profil @{target}: {e}")
            account_summary.append({"account": target, "scanned": 0, "matched": 0, "status": "Error akses"})
            continue

        print(f"[+] Nama Akun      : {profile.full_name} (@{profile.username})")
        print(f"[+] Total Postingan: {profile.mediacount}")
        print(f"[+] Folder Simpan  : {out_dir}")
        print("-" * 60)

        scanned = 0
        matched = 0
        stopped_early = False
        rate_limited = False

        try:
            for post in profile.get_posts():
                scanned += 1
                global_scanned += 1
                caption = post.caption or ""
                cap_lower = caption.lower()
                kind = "Video" if post.is_video else "Foto/Korsel"
                date_str = post.date_local.strftime("%Y-%m-%d %H:%M")
                preview = caption.replace("\n", " ")[:60]

                print(f"[{scanned}] [{date_str}] [{kind}] {post.shortcode}")
                if preview:
                    print(f"    Caption: \"{preview}...\"")

                # Cocokkan kata kunci dan tagar
                hit_keywords = [k for k in keywords if k in cap_lower]
                hit_hashtags = [h for h in hashtags if h in cap_lower]
                all_hits = hit_keywords + hit_hashtags

                if all_hits:
                    matched += 1
                    global_matched += 1
                    print(f"    >>> Cocok ({', '.join(all_hits)}). Mengunduh...")
                    try:
                        loader.download_post(post, target=out_dir)
                        print("    [✓] Berhasil diunduh.")
                    except Exception as dl_err:
                        print(f"    [!] Error saat mengunduh: {dl_err}")
                else:
                    print("    [-] Tidak cocok, dilewati.")

                print("-" * 60)

                if max_posts > 0 and scanned >= max_posts:
                    print(f"[*] Batas {max_posts} postingan untuk @{target} tercapai.")
                    break

                time.sleep(random.uniform(1.2, 1.8))

        except KeyboardInterrupt:
            print(f"\n[!] Pemindaian @{target} dihentikan pengguna.")
            stopped_early = True
        except PrivateProfileNotFollowedException:
            print(f"\n[x] Akun @{target} privat dan Anda belum follow.")
        except TooManyRequestsException:
            print("\n[!] Rate limit Instagram tercapai (429 Too Many Requests).")
            print("    Solusi: Nyalakan Mode Pesawat di HP selama 5 detik lalu matikan lagi untuk ganti IP.")
            rate_limited = True
        except Exception as e:
            print(f"\n[x] Kendala saat memindai: {e}")

        account_summary.append({
            "account": target,
            "scanned": scanned,
            "matched": matched,
            "status": "Selesai" if not rate_limited else "Rate limit"
        })

        if stopped_early or rate_limited:
            break

        if acc_idx < total_accounts:
            print("\n[*] Jeda 3 detik sebelum melanjutkan ke target berikutnya...")
            time.sleep(3)

    # Rekapitulasi Akhir
    print("\n" + "=" * 60)
    print(" REKAPITULASI PEMINDAIAN KESELURUHAN")
    print("=" * 60)
    print(f" Total Akun Diproses  : {len(account_summary)} dari {total_accounts}")
    print(f" Total Postingan Dicek: {global_scanned}")
    print(f" Total Cocok Diunduh  : {global_matched}")
    print("-" * 60)
    print(f" {'Akun Target':<22} | {'Dicek':<8} | {'Cocok':<8} | {'Status'}")
    print("-" * 60)
    for s in account_summary:
        print(f" @{s['account']:<21} | {s['scanned']:<8} | {s['matched']:<8} | {s['status']}")
    print("=" * 60)

    if global_matched > 0 and sys.platform.startswith("win"):
        try:
            os.startfile(str(OUTPUT_DIR))
        except Exception:
            pass

    input("\nTekan Enter untuk keluar...")


if __name__ == "__main__":
    main()
