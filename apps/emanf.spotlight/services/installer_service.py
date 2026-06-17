import shutil
import urllib.request
from pathlib import Path
from typing import Callable, Optional
import hashlib
import zipfile


class InstallerService:
    def __init__(self, apps_dir: Path = None, cache_dir: Path = None):
        self.apps_dir = apps_dir
        self.cache_dir = cache_dir

        if self.apps_dir is None:
            self._discover_apps_dir()
        if self.cache_dir is None:
            self._discover_cache_dir()

    def _discover_apps_dir(self):
        try:
            from core.paths import get_apps_dir

            self.apps_dir = Path(get_apps_dir())
        except Exception:
            current = Path(__file__).resolve()
            for parent in current.parents:
                apps_candidate = parent / "apps"
                if apps_candidate.exists():
                    self.apps_dir = apps_candidate
                    return
            self.apps_dir = Path.cwd() / "apps"

    def _discover_cache_dir(self):
        try:
            from core.paths import get_cache_dir

            self.cache_dir = Path(get_cache_dir())
        except Exception:
            home = Path.home()
            self.cache_dir = home / ".edock" / "cache"

    def install(
        self,
        app_id: str,
        download_url: str,
        expected_sha256: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        if not download_url:
            print("No download URL provided")
            return False

        temp_dir = self.cache_dir / "downloads" / app_id
        temp_dir.mkdir(parents=True, exist_ok=True)

        zip_path = temp_dir / f"{app_id}.zip"

        try:
            self._download_file(download_url, zip_path, progress_callback)

            if expected_sha256:
                actual_hash = self._calculate_sha256(zip_path)
                if actual_hash.lower() != expected_sha256.lower():
                    print(
                        f"Hash mismatch: expected {expected_sha256}, got {actual_hash}"
                    )
                    return False

            app_target = self.apps_dir / app_id
            self._extract_zip(zip_path, app_target)

            return True
        except Exception as e:
            print(f"Error installing {app_id}: {e}")
            return False
        finally:
            try:
                if zip_path.exists():
                    zip_path.unlink()
            except Exception:
                pass

    def _download_file(
        self, url: str, dest: Path, progress_callback: Optional[Callable] = None
    ):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "eDock-Spotlight/1.0",
            },
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(dest, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

    def _calculate_sha256(self, file_path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            while True:
                chunk = f.read(8192)
                if not chunk:
                    break
                sha256.update(chunk)
        return sha256.hexdigest()

    def _extract_zip(self, zip_path: Path, target_dir: Path):

        if target_dir.exists():
            shutil.rmtree(str(target_dir))

        target_dir.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(str(target_dir))
