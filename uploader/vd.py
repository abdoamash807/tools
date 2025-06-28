import requests
import os
import argparse

API_KEY = "7gp0z8rMBkj4bQVOjG9X5wKmZG2eLnY9XNJ"

def get_upload_server():
    url = f"https://api.vidguard.to/v1/upload/server?key={API_KEY}"
    response = requests.get(url)
    data = response.json()
    if data.get("status") == 200 and "result" in data and "url" in data["result"]:
        return data["result"]["url"]
    else:
        raise Exception(f"Failed to get upload server URL: {data}")

def upload_video(upload_url, video_path, folder_id=None):
    file_name = os.path.basename(video_path)
    with open(video_path, 'rb') as f:
        # Match curl's behavior: file tuple should include only filename
        files = {'file': (file_name, f, 'application/octet-stream')}
        data = {'key': API_KEY}
        if folder_id is not None:
            data['folder'] = str(folder_id)

        response = requests.post(upload_url, files=files, data=data)

    try:
        data = response.json()
    except Exception:
        raise Exception(f"Upload failed: {response.status_code}, {response.text}")

    if response.status_code == 200 and data.get("status") == 200:
        print("✅ Upload Successful!")
        video_url = data["result"]["URL"]
        id_part = video_url.split('v/')[-1]
        print(id_part)
    else:
        raise Exception(f"Upload error: {data}")

def main():
    parser = argparse.ArgumentParser(description="Upload a video to VidGuard.")
    parser.add_argument('video_path', type=str, help="Path to the video file.")
    parser.add_argument('--folder', type=int, default=None, help="Folder ID to upload the video into")
    args = parser.parse_args()

    try:
        upload_url = get_upload_server()
        upload_video(upload_url, args.video_path, args.folder)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    main()
