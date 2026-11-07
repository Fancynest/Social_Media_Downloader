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

    target = ""
    keywords = []
    max_posts = 50

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip().upper()
                v = v.strip()
                if k == "TARGET_AKUN":
                    target = extract_username(v)
                elif k == "KEYWORDS":
                    keywords = [item.strip().lower() for item in v.split(",") if item.strip()]
                elif k == "MAKSIMAL_POST":
                    try:
                        max_posts = int(v)
                    except ValueError:
                        max_posts = 0
    except Exception as e:
        print(f"[!] Gagal membaca {CONFIG_FILE.name}: {e}")

    return {"target": target, "keywords": keywords, "max_posts": max_posts} if (target and keywords) else None


def prompt_user_input():
    print("[*] Konfigurasi pencarian:\n")
    while True:
        raw_target = input("  -> Akun Target (username / link profil): ").strip()
        target = extract_username(raw_target)
        if target:
            break
        print("     [!] Username tidak boleh kosong.")

    while True:
        raw_kw = input("  -> Kata Kunci (pisahkan koma): ").strip()
        keywords = [k.strip().lower() for k in raw_kw.split(",") if k.strip()]
        if keywords:
            break
        print("     [!] Masukkan minimal satu kata kunci.")

    raw_max = input("  -> Maksimal postingan diperiksa (Enter untuk default 50, atau 0 untuk semua): ").strip()
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
                    f"TARGET_AKUN={target}\n"
                    f"KEYWORDS={', '.join(keywords)}\n"
                    f"MAKSIMAL_POST={max_posts}\n"
                )
            print("     [✓] Konfigurasi disimpan ke input_target.txt")
        except Exception as e:
            print(f"     [!] Gagal menyimpan konfigurasi: {e}")

    return {"target": target, "keywords": keywords, "max_posts": max_posts}


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
    print(" INSTAGRAM DOWNLOADER - FILTER KEYWORD CAPTION")
    print("=" * 60)

    config = read_config()
    if config:
        print("[*] Pengaturan aktif dari input_target.txt:")
        print(f"    - Target Akun   : @{config['target']}")
        print(f"    - Kata Kunci    : {', '.join(config['keywords'])}")
        print(f"    - Maksimal Post : {config['max_posts'] if config['max_posts'] > 0 else 'Semua'}")
        pilihan = input("\nGunakan pengaturan ini? (Y/n / ketik 'b' untuk input baru): ").strip().lower()
        if pilihan in ("n", "b", "no", "baru"):
            config = prompt_user_input()
    else:
        config = prompt_user_input()

    target = config["target"]
    keywords = config["keywords"]
    max_posts = config["max_posts"]

    loader = get_instaloader_instance()
    out_dir = OUTPUT_DIR / target
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[*] Mengambil profil @{target}...")
    try:
        profile = instaloader.Profile.from_username(loader.context, target)
    except ProfileNotExistsException:
        print(f"[x] Akun @{target} tidak ditemukan. Periksa kembali username.")
        input("\nTekan Enter untuk keluar...")
        return
    except LoginRequiredException:
        print("[x] Instagram meminta login untuk mengakses profil ini.")
        print("    Jalankan LOGIN_AKUN.bat menggunakan akun sekunder.")
        input("\nTekan Enter untuk keluar...")
        return
    except Exception as e:
        print(f"[x] Gagal mengakses profil: {e}")
        input("\nTekan Enter untuk keluar...")
        return

    print(f"[+] Akun ditemukan: {profile.full_name} (@{profile.username})")
    print(f"[+] Total Post    : {profile.mediacount}")
    print(f"[+] Folder Simpan : {out_dir}")
    print(f"[+] Filter Keyword: {', '.join(keywords)}")
    print("-" * 60)
    print("[*] Memulai pemindaian...\n")

    scanned = 0
    matched = 0

    try:
        for post in profile.get_posts():
            scanned += 1
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
                print(f"[*] Batas {max_posts} postingan tercapai.")
                break

            time.sleep(random.uniform(1.2, 1.8))

    except KeyboardInterrupt:
        print("\n[!] Dihentikan oleh pengguna.")
    except PrivateProfileNotFollowedException:
        print("\n[x] Akun ini privat dan akun Anda belum mem-follow akun ini.")
    except TooManyRequestsException:
        print("\n[!] Rate limit Instagram tercapai (429 Too Many Requests).")
        print("    Solusi: Nyalakan Mode Pesawat di HP selama 5 detik lalu matikan lagi untuk ganti IP.")
    except Exception as e:
        print(f"\n[x] Terjadi kendala: {e}")

    print("\n" + "=" * 60)
    print(" RINGKASAN PEMINDAIAN")
    print("=" * 60)
    print(f" Akun Target         : @{target}")
    print(f" Total Post Dicek    : {scanned}")
    print(f" Post Cocok Diunduh  : {matched}")
    print(f" Folder Penyimpanan  : {out_dir}")
    print("=" * 60)

    if matched > 0 and sys.platform.startswith("win"):
        try:
            os.startfile(str(out_dir))
        except Exception:
            pass

    input("\nTekan Enter untuk keluar...")


if __name__ == "__main__":
    main()
