import os
import json
import subprocess

API_KEY = "679b611b-24e6-42d4-b343-188dc4ba3b8e"
VIDEO_PATH = "/path/to/your/video.mp4"  # 🔁 Change this path to your MP4 file

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
        file_id = response_json.get("id")
        if file_id:
            print(f"✅ Uploaded successfully: https://pixeldrain.com/api/file/{file_id}")
        else:
            print("❌ Upload failed: No file ID returned.")
    except Exception as e:
        print(f"❌ Error uploading file: {e}")

if __name__ == "__main__":
    if not os.path.exists(VIDEO_PATH):
        print(f"❌ File not found: {VIDEO_PATH}")
    else:
        upload_with_curl(VIDEO_PATH, API_KEY)