import requests
import json

ACCESS_TOKEN = "vk1.a.eymMoZyjcCsp78iISnvSXNpCyLLYP1JTIaA2iS9XqdlakM1kf75ALres_K5AmTWiQj2ALYbbs1r6VD421H_A7wqymG-VVoQSl4hOXvmy03_HdBTjqBLSbZS0amZCwQw_cXmb9xDkFX1odWcZPNxI62Nm5iWuM4vQ39-cGqExS0hnycAKs1RdsuZUsH2bhw2GniJNP8v5B-Udo_Zr2DdrPQ" # Your token
COMMUNITY_ID = 229795703 # Your community ID
FILE_PATH = "/workspaces/codespaces-blank/dune.mp4" # Path to the document you want to upload
DOC_TITLE = "My Community Document" # Title for the document

# Step 1: Get upload server URL using docs.getWallUploadServer
get_upload_server_url = f"https://api.vk.com/method/docs.getWallUploadServer?group_id={COMMUNITY_ID}&access_token={ACCESS_TOKEN}&v=5.199"
response = requests.get(get_upload_server_url)
upload_server_data = response.json()

if 'response' in upload_server_data and 'upload_url' in upload_server_data['response']:
    upload_url = upload_server_data['response']['upload_url']
    print(f"Upload URL: {upload_url}")

    # Step 2: Upload the file
    with open(FILE_PATH, 'rb') as f:
        # Determine the correct MIME type. For .ts, it might be 'video/mp2t' or 'application/octet-stream'
        # If it's a video segment, 'video/mp2t' is more appropriate. If it's just a generic file, 'application/octet-stream'
        # For a .ts file, let's try 'video/mp2t' first.
        files = {'file': (FILE_PATH, f, 'video/mp2t')}
        upload_response = requests.post(upload_url, files=files)
        uploaded_file_data = upload_response.json()
        print(f"Uploaded file data: {uploaded_file_data}")

        if 'file' in uploaded_file_data:
            uploaded_file_string = uploaded_file_data['file']

            # Step 3: Save the document
            save_doc_url = f"https://api.vk.com/method/docs.save?file={uploaded_file_string}&title={DOC_TITLE}&access_token={ACCESS_TOKEN}&v=5.199"
            save_doc_response = requests.get(save_doc_url)
            saved_doc_data = save_doc_response.json()
            print(f"Saved document data: {saved_doc_data}")

            if 'response' in saved_doc_data and saved_doc_data['response']:
                print("Document uploaded and saved successfully!")
                # You can access the document details like saved_doc_data['response'][0]['id']
            else:
                print(f"Error saving document: {saved_doc_data}")
        else:
            print(f"Error uploading file: {uploaded_file_data}")
else:
    print(f"Error getting upload server URL: {upload_server_data}")