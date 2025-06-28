import asyncio
import aiofiles
import os
import re
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
import time

API_KEY = "679b611b-24e6-42d4-b343-188dc4ba3b8e"
SEGMENT_DIR = "/workspaces/codespaces-blank/output/media-1"
PLAYLIST_PATH = os.path.join(SEGMENT_DIR, "stream.m3u8")
OUTPUT_PLAYLIST = os.path.join(SEGMENT_DIR, "stream-uploaded.m3u8")

def upload_with_curl(file_path, api_key):
    try:
        result = subprocess.run(
            [
                "curl", "-s",
                "--connect-timeout", "10",
                "--max-time", "300",
                "--retry", "3",
                "--retry-delay", "1",
                "--compressed",
                "--http2",
                "-T", file_path,
                "-u", f":{api_key}",
                "https://pixeldrain.com/api/file/"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        response_json = json.loads(result.stdout)
        return response_json.get("id")
    except Exception as e:
        print(f"❌ Failed to upload {file_path}: {e}")
        return None

async def upload_file(executor, filepath):
    filename = os.path.basename(filepath)
    
    # Run curl upload in thread pool to make it non-blocking
    loop = asyncio.get_event_loop()
    file_id = await loop.run_in_executor(executor, upload_with_curl, filepath, API_KEY)
    
    if file_id:
        return filename, f"https://pixeldrain.com/api/file/{file_id}"
    else:
        return filename, None

async def upload_all_segments():
    segment_map = {}
    
    # Get all .ts files first
    ts_files = [f for f in os.listdir(SEGMENT_DIR) if f.endswith(".ts")]
    total_files = len(ts_files)
    print(f"📦 Found {total_files} segments to upload")
    
    # Use more workers for faster uploads
    max_workers = min(20, total_files)  # Adaptive worker count
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        tasks = []
        start_time = time.time()
        
        for filename in sorted(ts_files):
            filepath = os.path.join(SEGMENT_DIR, filename)
            tasks.append(upload_file(executor, filepath))
        
        # Process uploads with progress tracking
        completed = 0
        for task in asyncio.as_completed(tasks):
            filename, url = await task
            if url:
                segment_map[filename] = url
            completed += 1
            elapsed = time.time() - start_time
            rate = completed / elapsed if elapsed > 0 else 0
            print(f"📊 Progress: {completed}/{total_files} ({completed/total_files*100:.1f}%) - {rate:.1f} files/sec")
    
    total_time = time.time() - start_time
    print(f"⚡ Upload completed in {total_time:.2f}s - Average: {len(segment_map)/total_time:.1f} files/sec")
    return segment_map

async def update_playlist(segment_map):
    start_time = time.time()
    async with aiofiles.open(PLAYLIST_PATH, "r") as f:
        content = await f.read()

    for old_name, new_url in segment_map.items():
        content = re.sub(rf'\b{re.escape(old_name)}\b', new_url, content)

    async with aiofiles.open(OUTPUT_PLAYLIST, "w") as f:
        await f.write(content)

    elapsed = time.time() - start_time
    print(f"🎉 Playlist updated in {elapsed:.2f}s and saved to: {OUTPUT_PLAYLIST}")

async def upload_playlist():
    # Run playlist upload in thread pool to make it non-blocking
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=1) as executor:
        playlist_id = await loop.run_in_executor(executor, upload_with_curl, OUTPUT_PLAYLIST, API_KEY)
    
    if playlist_id:
        print(f"\n📄 Playlist uploaded: https://pixeldrain.com/api/file/{playlist_id}")
    else:
        print("❌ Failed to upload playlist")

async def main():
    segment_map = await upload_all_segments()
    await update_playlist(segment_map)
    await upload_playlist()

if __name__ == "__main__":
    asyncio.run(main())