import subprocess
import os
import shutil

async def download_aria2c(download_dir, download_target, renamed_folder="downloaded_content"):
    """
    Download a file using aria2c, rename the result folder, and return new path.
    """
    try:
        os.makedirs(download_dir, exist_ok=True)

        cmd = [
            "aria2c",
            "--dir=" + download_dir,
            "--continue=true",
            "--enable-dht=true",
            "--enable-peer-exchange=true",
            "--bt-save-metadata=true",
            "--seed-time=0",
            "--max-upload-limit=1K",
            download_target
        ]

        subprocess.run(cmd, check=True)

        # Find the newly created folder inside download_dir
        entries = os.listdir(download_dir)
        entries = [e for e in entries if os.path.isdir(os.path.join(download_dir, e))]
        if not entries:
            return os.path.abspath(download_dir)

        # Assume the last modified folder is the one we just downloaded
        entries.sort(key=lambda e: os.path.getmtime(os.path.join(download_dir, e)), reverse=True)
        original_path = os.path.join(download_dir, entries[0])
        new_path = os.path.join(download_dir, renamed_folder)

        if os.path.exists(new_path):
            shutil.rmtree(new_path)  # Remove if already exists

        os.rename(original_path, new_path)
        return new_path

    except subprocess.CalledProcessError:
        print("aria2c failed to download the file.")
        return None
    except FileNotFoundError:
        print("aria2c is not installed or not in your PATH.")
        return None

if __name__ == "__main__":
    final_path = download_aria2c(
        ".",
        "magnet:?xt=urn%3Abtih%3AD0D14B9BB19ABA83C012E019849E0D145372E74A&dn=Kryptic+%282024%29&tr=udp%3A%2F%2Ftracker.openbittorrent.com%3A80%2Fannounce&tr=udp%3A%2F%2Ftracker.opentrackr.org%3A1337%2Fannounce&tr=udp%3A%2F%2Ftracker.coppersurfer.tk%3A6969%2Fannounce&tr=udp%3A%2F%2Ftracker.leechers-paradise.org%3A6969%2Fannounce",
        renamed_folder="Dune2024"
    )
    print("Downloaded to:", final_path)
