import asyncio
import aiofiles
import os
import re
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
import time

SEGMENT_DIR = "/workspaces/codespaces-blank/output/media-1"
PLAYLIST_PATH = os.path.join(SEGMENT_DIR, "stream.m3u8")
OUTPUT_PLAYLIST = os.path.join(SEGMENT_DIR, "stream-uploaded.m3u8")

def upload_with_curl(file_path, max_retries=5):
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                [
                    "curl", "-s",
                    "--connect-timeout", "30",  # Increased from 10
                    "--max-time", "600",         # Increased from 300
                    "--retry", "2",              # Reduced internal retries
                    "--retry-delay", "2",        # Increased delay
                    "--compressed",
                    "-F", "reqtype=fileupload",
                    "-F", f"fileToUpload=@{file_path}",
                    "https://catbox.moe/user/api.php"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            # Catbox returns the direct URL as plain text
            url = result.stdout.strip()
            if url.startswith("https://files.catbox.moe/"):
                return url
            else:
                print(f"❌ Unexpected response from Catbox (attempt {attempt + 1}): {url}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return None
        except subprocess.CalledProcessError as e:
            if e.returncode == 28:  # Timeout error
                print(f"⏰ Timeout uploading {os.path.basename(file_path)} (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            else:
                print(f"❌ Upload error for {os.path.basename(file_path)}: curl exit code {e.returncode}")
                break
        except Exception as e:
            print(f"❌ Failed to upload {os.path.basename(file_path)} (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            break
    
    return None

async def upload_file(executor, filepath):
    filename = os.path.basename(filepath)
    # Run curl upload in thread pool to make it non-blocking
    loop = asyncio.get_event_loop()
    url = await loop.run_in_executor(executor, upload_with_curl, filepath)
    if url:
        return filename, url
    else:
        return filename, None

async def upload_all_segments():
    segment_map = {}
    failed_files = []
    
    # Get all .ts files first
    ts_files = [f for f in os.listdir(SEGMENT_DIR) if f.endswith(".ts")]
    total_files = len(ts_files)
    print(f"📦 Found {total_files} segments to upload")
    
    # Reduced workers to avoid overwhelming Catbox
    max_workers = min(8, total_files)  # Reduced from 20 to 8
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
            else:
                failed_files.append(filename)
                completed += 1  # Still count as processed
    
    total_time = time.time() - start_time
    success_count = len(segment_map)
    print(f"⚡ Upload completed in {total_time:.2f}s")
    print(f"✅ Successful: {success_count}/{total_files} ({success_count/total_files*100:.1f}%)")
    
    if failed_files:
        print(f"❌ Failed uploads: {len(failed_files)} files")
        print("Failed files:", ", ".join(failed_files[:10]) + ("..." if len(failed_files) > 10 else ""))
        
        # Attempt to retry failed files with lower concurrency
        if failed_files:
            print("\n🔄 Retrying failed uploads with single-threaded approach...")
            retry_start = time.time()
            with ThreadPoolExecutor(max_workers=1) as retry_executor:
                for filename in failed_files:
                    filepath = os.path.join(SEGMENT_DIR, filename)
                    print(f"🔄 Retrying {filename}...")
                    url = await upload_file(retry_executor, filepath)
                    if url[1]:  # url is a tuple (filename, url)
                        segment_map[filename] = url[1]
                        print(f"✅ Retry successful: {filename}")
                    else:
                        print(f"❌ Retry failed: {filename}")
                    
                    # Add delay between retries to be respectful
                    await asyncio.sleep(1)
            
            retry_time = time.time() - retry_start
            print(f"🔄 Retry phase completed in {retry_time:.2f}s")
    
    final_success = len(segment_map)
    print(f"🎯 Final result: {final_success}/{total_files} files uploaded successfully")
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
        playlist_url = await loop.run_in_executor(executor, upload_with_curl, OUTPUT_PLAYLIST)
        if playlist_url:
            print(f"\n📄 Playlist uploaded: {playlist_url}")
        else:
            print("❌ Failed to upload playlist")

async def main():
    segment_map = await upload_all_segments()
    await update_playlist(segment_map)
    await upload_playlist()

if __name__ == "__main__":
    asyncio.run(main())