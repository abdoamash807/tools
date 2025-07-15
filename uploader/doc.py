import requests
import os

ACCESS_TOKEN = "vk1.a.eymMoZyjcCsp78iISnvSXNpCyLLYP1JTIaA2iS9XqdlakM1kf75ALres_K5AmTWiQj2ALYbbs1r6VD421H_A7wqymG-VVoQSl4hOXvmy03_HdBTjqBLSbZS0amZCwQw_cXmb9xDkFX1odWcZPNxI62Nm5iWuM4vQ39-cGqExS0hnycAKs1RdsuZUsH2bhw2GniJNP8v5B-Udo_Zr2DdrPQ"
COMMUNITY_ID = 229795703
VK_API_VERSION = "5.199"

def upload_doc_to_vk_wall(file_path: str, title: str = None):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    title = title or os.path.basename(file_path)

    # STEP 1: get upload URL
    resp = requests.get(
        "https://api.vk.com/method/docs.getWallUploadServer",
        params={
            "group_id": COMMUNITY_ID,
            "access_token": ACCESS_TOKEN,
            "v": VK_API_VERSION
        }
    )
    data = resp.json()
    if not data.get("response", {}).get("upload_url"):
        raise Exception(f"Failed to get upload URL: {data}")

    upload_url = data["response"]["upload_url"]
    print("→ Upload URL:", upload_url)

    # STEP 2: upload the file
    ext = os.path.splitext(file_path)[1].lower()
    mime = "video/mp2t" if ext == ".ts" else "application/octet-stream"

    with open(file_path, "rb") as fp:
        files = {"file": (os.path.basename(file_path), fp, mime)}
        upload_resp = requests.post(upload_url, files=files)

    # check HTTP
    if upload_resp.status_code != 200:
        raise Exception(f"Upload HTTP {upload_resp.status_code}: {upload_resp.text}")

    # try parse JSON
    try:
        upload_data = upload_resp.json()
    except ValueError:
        raise Exception(f"Upload response not JSON:\n{upload_resp.text}")

    if "file" not in upload_data:
        raise Exception(f"Upload failed, no 'file' in response: {upload_data}")

    print("→ Uploaded, got file param.")

    # STEP 3: save the document
    save_resp = requests.get(
        "https://api.vk.com/method/docs.save",
        params={
            "file": upload_data["file"],
            "title": title,
            "access_token": ACCESS_TOKEN,
            "v": VK_API_VERSION
        }
    )
    save_data = save_resp.json()
    if "response" not in save_data:
        raise Exception(f"Save failed: {save_data}")

    doc = save_data["response"]["doc"]
    return {
        "id":    f"doc{doc['owner_id']}_{doc['id']}",
    }

if __name__ == "__main__":
    result = upload_doc_to_vk_wall("/home/kda/Downloads/tt11001074.ara.srt", "Dune Movie")
    print("✅ Uploaded!")
    print("ID:", result["id"])