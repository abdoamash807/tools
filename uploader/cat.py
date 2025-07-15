import asyncio
import aiofiles
import os
import re
import subprocess
import time
import json
import logging
from concurrent.futures import ThreadPoolExecutor

# --- Configuration ---
MASTER_PLAYLIST_FILENAME = "master.m3u8"
MAX_WORKERS = 10
SEGMENT_EXTENSIONS = {".ts", ".aac"}
STATE_FILENAME = "uploaded_files.json" # File to store progress

# Get the directory where the script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SUCCESS_LOG_FILENAME = os.path.join(SCRIPT_DIR, "upload_success.log")
FAILURE_LOG_FILENAME = os.path.join(SCRIPT_DIR, "upload_failure.log")

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
success_logger = logging.getLogger('success')
failure_logger = logging.getLogger('failure')
success_handler = logging.FileHandler(SUCCESS_LOG_FILENAME)
failure_handler = logging.FileHandler(FAILURE_LOG_FILENAME)
success_logger.addHandler(success_handler)
failure_logger.addHandler(failure_handler)

# --- Core Upload & State Management ---
def upload_with_curl(file_path):
    """
    Uploads a file to Catbox, retries on failure. Returns URL or None.
    (This function no longer prints, just returns results)
    """
    for attempt in range(3):
        try:
            result = subprocess.run(
                [
                    "curl", "-s", "--connect-timeout", "20", "--max-time", "300",
                    "-F", "reqtype=fileupload",
                    "-F", f"fileToUpload=@{file_path}",
                    "https://catbox.moe/user/api.php"
                ],
                capture_output=True, text=True, check=True
            )
            url = result.stdout.strip()
            if url.startswith("https://files.catbox.moe/"):
                return url
        except Exception as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else: # Log final failure reason
                 logging.error(f"Final upload attempt failed for {os.path.basename(file_path)}. Error: {e}")
    return None

async def process_and_upload_segment(file_path, url_map, lock, state_file_path, loop, media_type):
    """
    Manages the upload for a single file, including checking state,
    uploading, and saving progress.
    """
    filename = os.path.basename(file_path)
    # Create unique key using media type and filename to prevent mixing qualities
    file_key = f"{media_type}_{filename}"

    # 1. Check if already uploaded
    if file_key in url_map:
        logging.info(f"⏭️  Skipping '{filename}' in {media_type}, already uploaded.")
        return url_map[file_key]

    # 2. If not, upload the file
    start_time = time.time()
    logging.info(f"⬆️  Uploading '{filename}' from {media_type}...")
    new_url = await loop.run_in_executor(None, upload_with_curl, file_path)
    upload_time = time.time() - start_time

    # 3. Update state and log result
    async with lock:
        if new_url:
            url_map[file_key] = new_url
            success_logger.info(f"SUCCESS: {media_type}/{filename} -> {new_url}")
            logging.info(f"✅ Success: '{filename}' in {media_type} ({upload_time:.1f}s)")
            # Write progress to state file immediately
            async with aiofiles.open(state_file_path, "w") as f:
                await f.write(json.dumps(url_map, indent=2))
            return new_url
        else:
            failure_logger.error(f"FAILURE: {media_type}/{filename}")
            logging.error(f"🚨 Failed to upload '{filename}' from {media_type} after all retries. ({upload_time:.1f}s)")
            return None

async def process_and_upload_playlist(playlist_path, url_map, lock, state_file_path, loop, media_type):
    """
    Handles playlist upload with proper logging and state management.
    """
    filename = os.path.basename(playlist_path)
    playlist_key = f"{media_type}_playlist_{filename}"
    
    # Check if playlist already uploaded
    if playlist_key in url_map:
        logging.info(f"⏭️  Skipping playlist '{filename}' in {media_type}, already uploaded.")
        return url_map[playlist_key]
    
    logging.info(f"⬆️  Uploading playlist '{filename}' from {media_type}...")
    new_url = await loop.run_in_executor(None, upload_with_curl, playlist_path)
    
    async with lock:
        if new_url:
            url_map[playlist_key] = new_url
            success_logger.info(f"SUCCESS: {media_type}/playlist/{filename} -> {new_url}")
            logging.info(f"✅ Success: playlist '{filename}' in {media_type}")
            # Write progress to state file immediately
            async with aiofiles.open(state_file_path, "w") as f:
                await f.write(json.dumps(url_map, indent=2))
            return new_url
        else:
            failure_logger.error(f"FAILURE: {media_type}/playlist/{filename}")
            logging.error(f"🚨 Failed to upload playlist '{filename}' from {media_type} after all retries.")
            return None

def remove_success_log_if_complete(state_file_path):
    """
    Remove success log file if all uploads completed successfully.
    """
    try:
        if os.path.exists(SUCCESS_LOG_FILENAME):
            os.remove(SUCCESS_LOG_FILENAME)
            logging.info("✅ Success log file removed - all uploads completed successfully")
    except Exception as e:
        logging.warning(f"Could not remove success log file: {e}")

# --- Main Application Logic ---
async def main(root_dir):
    """
    Orchestrates the entire HLS processing and upload workflow for a given directory.
    """
    start_time = time.time()
    master_playlist_path = os.path.join(root_dir, MASTER_PLAYLIST_FILENAME)
    state_file_path = os.path.join(root_dir, STATE_FILENAME)
    
    # Load the map of already uploaded files, or create an empty one
    try:
        async with aiofiles.open(state_file_path, "r") as f:
            url_map = json.loads(await f.read())
        logging.info(f"Loaded {len(url_map)} previously uploaded files from state file.")
    except (FileNotFoundError, json.JSONDecodeError):
        url_map = {}

    if not os.path.exists(master_playlist_path):
        return logging.error(f"🚨 Master playlist not found at '{master_playlist_path}'")

    async with aiofiles.open(master_playlist_path, "r") as f:
        master_content = await f.read()

    playlists_by_dir = {}
    all_playlists = re.findall(r'^(?!#).*\.m3u8$', master_content, re.M)
    all_playlists.extend(re.findall(r'URI="([^"]+)"', master_content))
    for p in set(all_playlists):
        dir_name = os.path.dirname(p)
        playlists_by_dir.setdefault(dir_name, []).append(p)

    logging.info(f"Found {len(playlists_by_dir)} media directories to process in '{root_dir}'.")
    master_url_map = {}
    loop = asyncio.get_event_loop()
    upload_lock = asyncio.Lock() # To safely write to the state file
    all_uploads_successful = True

    for rel_dir, playlists in playlists_by_dir.items():
        print(f"\n--- 📂 Processing: {rel_dir} ---")
        full_dir_path = os.path.join(root_dir, rel_dir)
        media_type = rel_dir if rel_dir else "root"  # Use directory name as media type identifier
        
        try:
            files_in_dir = os.listdir(full_dir_path)
        except FileNotFoundError:
            logging.warning(f"⚠️  Directory not found: '{full_dir_path}'. Skipping.")
            continue

        segment_files = sorted([os.path.join(full_dir_path, f) for f in files_in_dir if os.path.splitext(f)[1] in SEGMENT_EXTENSIONS])
        if not segment_files:
            logging.info("No media segments found. Skipping.")
            continue

        # Create concurrent upload tasks for all segments in this directory with limited concurrency
        semaphore = asyncio.Semaphore(MAX_WORKERS)
        
        async def limited_upload(file_path):
            async with semaphore:
                return await process_and_upload_segment(file_path, url_map, upload_lock, state_file_path, loop, media_type)
        
        tasks = [limited_upload(f) for f in segment_files]
        results = await asyncio.gather(*tasks)

        if None in results:
            logging.critical("🚫 ABORTING: Critical upload failure for one or more segments. Check failure log for details.")
            all_uploads_successful = False
            return

        print(f"   ✅ All {len(segment_files)} segments for '{rel_dir}' are uploaded and verified.")

        for rel_playlist in playlists:
            full_playlist_path = os.path.join(root_dir, rel_playlist)
            async with aiofiles.open(full_playlist_path, "r") as f_playlist:
                playlist_content = await f_playlist.read()
            
            # Replace filenames with URLs, using the media-type specific keys
            for file_key, url in url_map.items():
                if file_key.startswith(f"{media_type}_"):
                    # Extract original filename from the key
                    original_filename = file_key.replace(f"{media_type}_", "")
                    playlist_content = playlist_content.replace(original_filename, url)

            output_playlist_path = full_playlist_path.replace(".m3u8", "-uploaded.m3u8")
            async with aiofiles.open(output_playlist_path, "w") as f_out:
                await f_out.write(playlist_content)

            new_playlist_url = await process_and_upload_playlist(output_playlist_path, url_map, upload_lock, state_file_path, loop, media_type)
            if new_playlist_url is None:
                logging.critical(f"🚫 ABORTING: Failed to upload playlist '{os.path.basename(output_playlist_path)}'.")
                all_uploads_successful = False
                return
            
            print(f"   📄 Playlist updated and uploaded: {os.path.basename(rel_playlist)}")
            master_url_map[rel_playlist] = new_playlist_url

    print("\n--- 📝 Finalizing Master Playlist ---")
    for old_path, new_url in master_url_map.items():
        master_content = master_content.replace(old_path, new_url)
    
    output_master_path = os.path.join(root_dir, "master-uploaded.m3u8")
    async with aiofiles.open(output_master_path, "w") as f:
        await f.write(master_content)

    # Upload master playlist
    master_key = "master_playlist"
    if master_key in url_map:
        final_master_url = url_map[master_key]
        logging.info("⏭️  Master playlist already uploaded.")
    else:
        logging.info("⬆️  Uploading master playlist...")
        final_master_url = await loop.run_in_executor(None, upload_with_curl, output_master_path)
        if final_master_url:
            async with upload_lock:
                url_map[master_key] = final_master_url
                success_logger.info(f"SUCCESS: master_playlist -> {final_master_url}")
                async with aiofiles.open(state_file_path, "w") as f:
                    await f.write(json.dumps(url_map, indent=2))
        else:
            all_uploads_successful = False

    if final_master_url:
        print("\n" + "="*50)
        print("🎉 Success! Final Master Playlist URL:")
        print(final_master_url)
        print("="*50)
        
        # Remove success log if all uploads were successful
        if all_uploads_successful:
            remove_success_log_if_complete(state_file_path)
    else:
        print("\n❌ CRITICAL: Failed to upload the final master playlist.")
        all_uploads_successful = False

    print(f"Total time: {time.time() - start_time:.2f}s")


if __name__ == "__main__":
    target_root_directory = "/workspaces/tools/output"
    if not os.path.isdir(target_root_directory):
        print(f"Error: Root directory '{target_root_directory}' not found.")
    else:
        asyncio.run(main(target_root_directory))