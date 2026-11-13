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


def parse_cookie_file(cookie_path: Path) -> dict:
    """Membaca sessionid atau format cookies lainnya."""
    if not cookie_path.exists():
        return {}
    content = cookie_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not content:
        return {}

    cookies = {}
    for line in content.splitlines():
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
    if not cookies and len(content) > 10 and not any(c in content for c in "\n\t"):
        cookies["sessionid"] = content.strip().strip(";\"'")
    return cookies


def get_instaloader_instance(save_caption: bool = False) -> instaloader.Instaloader:
    """Membuat instance Instaloader dengan opsi format dan sesi tersimpan."""
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

    # Cek sesi lokal atau sesi parent folder
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
                    loader.load_session_from_file(username, str(s_file))
                    print(f"[*] Menggunakan sesi login akun: @{username}")
                    return loader
            except Exception:
                pass

    # Cek cookies dari input_cookie.txt
    cookies = parse_cookie_file(COOKIE_FILE)
    if "sessionid" in cookies:
        try:
            loader.context._session.cookies.set("sessionid", cookies["sessionid"], domain=".instagram.com")
            print("[*] Menggunakan cookie sessionid dari input_cookie.txt")
        except Exception:
            pass

    return loader


def main():
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
        except ProfileNotExistsException:
            print(f"[x] Akun @{target} tidak ditemukan. Melanjutkan ke target berikutnya...")
            summary_report.append({"target": target, "downloaded": 0, "status": "Tidak Ditemukan"})
            continue
        except LoginRequiredException:
            print(f"[x] Akun @{target} memerlukan login. Jalankan LOGIN_AKUN.bat.")
            summary_report.append({"target": target, "downloaded": 0, "status": "Perlu Login"})
            continue
        except Exception as e:
            print(f"[x] Gagal mengakses profil @{target}: {e}")
            summary_report.append({"target": target, "downloaded": 0, "status": f"Error: {e}"})
            continue

        print(f"[+] Nama Akun      : {profile.full_name} (@{profile.username})")
        print(f"[+] Total Postingan: {profile.mediacount}")
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
