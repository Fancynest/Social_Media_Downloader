# -*- coding: utf-8 -*-
import os
import sys
import time
import random
import getpass
import argparse
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import instaloader
from instaloader.exceptions import (
    ProfileNotExistsException,
    PrivateProfileNotFollowedException,
    LoginRequiredException,
    TooManyRequestsException,
    BadCredentialsException,
    TwoFactorAuthRequiredException,
)

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "input_target.txt"
SESSION_FILE = BASE_DIR / "session.dat"
USER_FILE = BASE_DIR / "session_user.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"


def extract_username(val: str) -> str:
    s = val.strip().rstrip("/")
    if "instagram.com/" in s:
        parts = s.split("instagram.com/")[1].split("?")[0].split("/")
        s = parts[0] if parts else s
    return s.lstrip("@").strip()


def read_config():
    if not CONFIG_FILE.exists():
        return None

    targets = []
    keywords = []
    max_posts = 50
    current_key = None

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
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
                    for item in val.split(","):
                        cleaned = extract_username(item)
                        if cleaned and cleaned not in targets:
                            targets.append(cleaned)
                elif current_key == "KEYWORDS":
                    for item in val.split(","):
                        k_clean = item.strip().lower()
                        if k_clean and k_clean not in keywords:
                            keywords.append(k_clean)
                elif current_key == "MAKSIMAL_POST":
                    try:
                        max_posts = int(val)
                    except ValueError:
                        pass
    except Exception as e:
        print(f"[!] Gagal membaca {CONFIG_FILE.name}: {e}")

    return {"targets": targets, "keywords": keywords, "max_posts": max_posts} if (targets and keywords) else None


def prompt_user_input():
    print("[*] Konfigurasi pencarian:\n")
    while True:
        raw_target = input("  -> Akun Target (bisa 1 atau banyak akun, pisahkan koma): ").strip()
        targets = []
        for item in raw_target.split(","):
            cleaned = extract_username(item)
            if cleaned and cleaned not in targets:
                targets.append(cleaned)
        if targets:
            break
        print("     [!] Masukkan minimal satu username / link akun yang valid.")

    while True:
        raw_kw = input("  -> Kata Kunci (pisahkan koma): ").strip()
        keywords = [k.strip().lower() for k in raw_kw.split(",") if k.strip()]
        if keywords:
            break
        print("     [!] Masukkan minimal satu kata kunci.")

    raw_max = input("  -> Maksimal postingan per akun (Enter untuk default 50, atau 0 untuk semua): ").strip()
    try:
        max_posts = int(raw_max) if raw_max else 50
    except ValueError:
        max_posts = 50

    save = input("\n  -> Simpan ke input_target.txt? (Y/n, default Y): ").strip().lower()
    if save in ("", "y", "ya", "yes"):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                f.write(
                    "# Pengaturan Target Download Instagram\n"
                    f"TARGET_AKUN={', '.join(targets)}\n"
                    f"KEYWORDS={', '.join(keywords)}\n"
                    f"MAKSIMAL_POST={max_posts}\n"
                )
            print("     [✓] Konfigurasi disimpan ke input_target.txt")
        except Exception as e:
            print(f"     [!] Gagal menyimpan konfigurasi: {e}")

    return {"targets": targets, "keywords": keywords, "max_posts": max_posts}


def login_interactive():
    print("=" * 60)
    print(" AUTENTIKASI AKUN INSTAGRAM (OPSIONAL)")
    print("=" * 60)
    print("1. Cookie 'sessionid' browser (Rekomendasi, anti-checkpoint)")
    print("2. Login langsung (Username & Password)\n")

    choice = input("Pilih metode (1/2, default 1): ").strip()
    if choice != "2":
        print("\nCara ambil sessionid dari browser:")
        print("1. Buka instagram.com yang sudah login di Chrome/Edge.")
        print("2. Tekan F12 -> tab Application -> Cookies -> https://www.instagram.com")
        print("3. Salin isi Value dari 'sessionid'.\n")

        session_id = input("Paste nilai sessionid: ").strip().strip('"').strip("'")
        if not session_id:
            print("[x] Cookie sessionid kosong.")
            return

        loader = instaloader.Instaloader()
        loader.context._session.cookies.set("sessionid", session_id, domain=".instagram.com")
        try:
            username = loader.test_login()
            if username:
                loader.context.username = username
                loader.save_session_to_file(str(SESSION_FILE))
                with open(USER_FILE, "w", encoding="utf-8") as f:
                    f.write(username)
                print(f"[✓] Berhasil login sebagai @{username}. Sesi disimpan.")
            else:
                print("[x] sessionid tidak valid atau sesi sudah expired.")
        except Exception as e:
            print(f"[x] Verifikasi sessionid gagal: {e}")
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


def get_instaloader_instance():
    loader = instaloader.Instaloader(
        sleep=False,
        download_pictures=True,
        download_videos=True,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        post_metadata_txt_pattern="{caption}",
        filename_pattern="{date_utc:%Y-%m-%d_%H-%M-%S}_{shortcode}",
    )

    if SESSION_FILE.exists() and USER_FILE.exists():
        try:
            with open(USER_FILE, "r", encoding="utf-8") as f:
                saved_user = f.read().strip()
            if saved_user:
                loader.load_session_from_file(saved_user, str(SESSION_FILE))
                print(f"[+] Menggunakan sesi login akun: @{saved_user}")
                return loader
        except Exception as e:
            print(f"[!] Sesi tersimpan tidak dapat dimuat ({e}), beralih ke Mode Tamu.")

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
    print(" INSTAGRAM DOWNLOADER - FILTER KEYWORD CAPTION (BATCH)")
    print("=" * 60)

    config = read_config()
    if config:
        print(f"[*] Ditemukan {len(config['targets'])} akun target di input_target.txt:")
        for t in config['targets']:
            print(f"    - @{t}")
        print(f"[*] Kata Kunci    : {', '.join(config['keywords'])}")
        print(f"[*] Batas Per Akun: {config['max_posts'] if config['max_posts'] > 0 else 'Semua postingan'}")
        pilihan = input("\nGunakan pengaturan ini? (Y/n / ketik 'b' untuk input baru): ").strip().lower()
        if pilihan in ("n", "b", "no", "baru"):
            config = prompt_user_input()
    else:
        config = prompt_user_input()

    targets = config["targets"]
    keywords = config["keywords"]
    max_posts = config["max_posts"]

    loader = get_instaloader_instance()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_accounts = len(targets)
    global_scanned = 0
    global_matched = 0
    account_summary = []

    for acc_idx, target in enumerate(targets, 1):
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
        print(f"[+] Filter Keyword : {', '.join(keywords)}")
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

                hit_keywords = [k for k in keywords if k in cap_lower]
                if hit_keywords:
                    matched += 1
                    global_matched += 1
                    print(f"    >>> Cocok ({', '.join(hit_keywords)}). Mengunduh...")
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
    print(f" Total Akun Diproses : {len(account_summary)} dari {total_accounts}")
    print(f" Total Postingan Dicek: {global_scanned}")
    print(f" Total Cocok Diunduh : {global_matched}")
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
