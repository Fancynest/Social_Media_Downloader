# -*- coding: utf-8 -*-
import os
import sys
import re
import time
import random
import shutil
import subprocess
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import instaloader
except ImportError:
    import subprocess
    print("[*] Menyiapkan paket library (instaloader)...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "instaloader>=4.10"])
    import instaloader

from instaloader.exceptions import TooManyRequestsException


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

    def patched_doc_id(self, doc_id: str, variables: dict, referer=None, web_api: bool = True):
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
                raise instaloader.exceptions.ProfileNotExistsException(f"Profile {username} does not exist.")

            if "Sorry, this page isn't available" in html or "Halaman ini tidak tersedia" in html:
                raise instaloader.exceptions.ProfileNotExistsException(f"Profile {username} does not exist.")

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
                raise instaloader.exceptions.ProfileNotExistsException(f"Profile {username} does not exist.")

        if profile and hasattr(profile, "_node") and isinstance(profile._node, dict):
            profile._node = cls._normalize_profile_data(profile._node)
            profile._has_full_metadata = True

        return profile

    instaloader.Profile.from_username = classmethod(patched_from_username)

    # 4. Patch test_login agar mendeteksi sesi web langsung
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

BASE_DIR = Path(__file__).resolve().parent
LINKS_FILE = BASE_DIR / "link_instagram.txt"
HISTORY_FILE = BASE_DIR / "download_history.txt"
OUTPUT_DIR = BASE_DIR / "Hasil_Download"
SESSION_FILE = BASE_DIR / "session.dat"
USER_FILE = BASE_DIR / "session_user.txt"


def find_ytdlp():
    bin_path = shutil.which("yt-dlp")
    if bin_path:
        return bin_path
    winget_path = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "WinGet" / "Packages"
    for match in winget_path.glob("**/yt-dlp.exe"):
        if match.is_file():
            return str(match)
    return None


def extract_shortcode(url: str):
    m = re.search(r"/(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)", url)
    if m:
        return m.group(1)
    clean = url.strip().strip("/").split("?")[0].split("/")[-1]
    if 9 <= len(clean) <= 15 and re.match(r"^[A-Za-z0-9_-]+$", clean):
        return clean
    return None


def load_history():
    if not HISTORY_FILE.exists():
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8", errors="ignore") as f:
        return set(line.strip() for line in f if line.strip())


def append_history(item: str):
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(f"{item}\n")
    except Exception:
        pass


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
        (BASE_DIR.parent / "1_Filter_Berdasarkan_Keyword" / "session.dat", BASE_DIR.parent / "1_Filter_Berdasarkan_Keyword" / "session_user.txt"),
    ]
    for s_file, u_file in session_locations:
        if s_file.exists() and u_file.exists():
            try:
                with open(u_file, "r", encoding="utf-8") as f:
                    saved_user = f.read().strip()
                if saved_user:
                    loader.load_session_from_file(saved_user, str(s_file))
                    print(f"[+] Sesi aktif: @{saved_user}")
                    return loader
            except Exception:
                pass
    print("[+] Berjalan dalam Mode Tamu (Tanpa login)")
    return loader


def download_with_gallery_dl(url: str, output_folder: Path) -> bool:
    try:
        cmd = [
            sys.executable, "-m", "gallery_dl",
            "-d", str(output_folder),
            "--no-mtime",
            url
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace", timeout=120)
        return res.returncode == 0
    except Exception:
        return False


def download_with_ytdlp(ytdlp_bin: str, url: str, output_folder: Path) -> bool:
    try:
        cmd = [
            ytdlp_bin,
            "--no-warnings",
            "--no-playlist",
            "-P", str(output_folder),
            "-o", "%(upload_date>%Y-%m-%d)s_%(id)s.%(ext)s",
            url
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", errors="replace")
        return res.returncode == 0
    except Exception:
        return False


def main():
    print("=" * 60)
    print(" INSTAGRAM MASS DOWNLOADER (DAFTAR TAUTAN)")
    print("=" * 60)

    if not LINKS_FILE.exists():
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            f.write("# Tempelkan link postingan / reel Instagram di sini (1 per baris):\n")
        print(f"[!] Berkas '{LINKS_FILE.name}' telah dibuat. Silakan isi link yang ingin diunduh.")
        input("\nTekan Enter untuk keluar...")
        return

    save_caption = False
    links = []
    with open(LINKS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if line.upper().startswith("SIMPAN_CAPTION="):
                val = line.split("=", 1)[1].strip().lower()
                save_caption = val in ("ya", "yes", "true", "1", "y")
                continue
            if not line.startswith("#"):
                links.append(line)

    if not links:
        print(f"[!] '{LINKS_FILE.name}' masih kosong. Isi link terlebih dahulu.")
        input("\nTekan Enter untuk keluar...")
        return

    history = load_history()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ytdlp_bin = find_ytdlp()

    print(f" Folder Simpan : {OUTPUT_DIR}")
    print(f" Total Tautan  : {len(links)}")
    print(f" Simpan Caption: {'Ya (.txt)' if save_caption else 'Tidak (Hanya Foto/Video)'}\n")

    loader = get_instaloader_instance(save_caption=save_caption)
    success, skipped, failed = 0, 0, 0

    for idx, url in enumerate(links, 1):
        shortcode = extract_shortcode(url)
        print(f"[{idx}/{len(links)}] Memproses: {url}")

        if not shortcode:
            print("    [x] Format URL tidak dikenali.")
            failed += 1
            print("-" * 60)
            continue

        if shortcode in history or url in history:
            print("    [i] Sudah pernah diunduh (dilewati).")
            skipped += 1
            print("-" * 60)
            continue

        downloaded = False
        try:
            post = instaloader.Post.from_shortcode(loader.context, shortcode)
            kind = "Video" if post.is_video else "Foto/Korsel"
            print(f"    Tipe: {kind} | Pemilik: @{post.owner_username or 'unknown'}")
            loader.download_post(post, target=OUTPUT_DIR)
            print("    [✓] Berhasil diunduh.")
            downloaded = True
        except TooManyRequestsException:
            print("    [!] Rate limit Instaloader tercapai.")
            if ytdlp_bin:
                print("    --> Mencoba fallback via yt-dlp...")
                if download_with_ytdlp(ytdlp_bin, url, OUTPUT_DIR):
                    print("    [✓] Berhasil diunduh via yt-dlp.")
                    downloaded = True
            if not downloaded:
                print("    --> Mencoba fallback via gallery-dl...")
                if download_with_gallery_dl(url, OUTPUT_DIR):
                    print("    [✓] Berhasil diunduh via gallery-dl.")
                    downloaded = True
        except Exception as e:
            if ytdlp_bin:
                print(f"    [!] Instaloader gagal ({e}), mencoba yt-dlp...")
                if download_with_ytdlp(ytdlp_bin, url, OUTPUT_DIR):
                    print("    [✓] Berhasil diunduh via yt-dlp.")
                    downloaded = True
            if not downloaded:
                print("    --> Mencoba fallback via gallery-dl...")
                if download_with_gallery_dl(url, OUTPUT_DIR):
                    print("    [✓] Berhasil diunduh via gallery-dl.")
                    downloaded = True

        if downloaded:
            success += 1
            append_history(shortcode)
            append_history(url)
        else:
            failed += 1
            print("    [x] Gagal mengunduh postingan ini.")

        print("-" * 60)
        time.sleep(random.uniform(1.2, 1.8))

    print("\n" + "=" * 60)
    print(" RINGKASAN PENGUNDUHAN")
    print("=" * 60)
    print(f" Total Diproses : {len(links)}")
    print(f" Berhasil       : {success}")
    print(f" Dilewati       : {skipped}")
    print(f" Gagal          : {failed}")
    print(f" Lokasi File    : {OUTPUT_DIR}")
    print("=" * 60)

    if success > 0 and sys.platform.startswith("win"):
        try:
            os.startfile(str(OUTPUT_DIR))
        except Exception:
            pass

    input("\nTekan Enter untuk keluar...")


if __name__ == "__main__":
    main()
