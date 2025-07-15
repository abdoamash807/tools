from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import tempfile
import threading
import time
from datetime import datetime
import uuid
import traceback

# Import your existing scripts
import ok
import dzen
import vk  # Your VK Video script (save the first artifact as vk.py)

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = '/tmp/uploads'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'webm', 'flv', '3gp'}
MAX_CONTENT_LENGTH = 20 * 1024 * 1024 * 1024  # 20GB max file size

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Store upload status
upload_status = {}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def upload_to_platform(platform, video_path, upload_id, title=None):
    """Background task to upload video to specified platform"""
    try:
        upload_status[upload_id]['status'] = 'uploading'
        upload_status[upload_id]['message'] = f'Uploading to {platform}...'
        upload_status[upload_id]['progress'] = 25
        
        if platform == 'ok':
            # Use the modified OK script
            result = ok.main_with_path(video_path)
        elif platform == 'dzen':
            # Use the modified Dzen script with title
            result = dzen.main_with_path(video_path, title or "Uploaded Video")
        elif platform == 'vk':
            # Use the VK Video script with title
            result = vk.main_with_path(video_path, title or "Uploaded Video")
        else:
            raise ValueError(f"Unknown platform: {platform}")
        
        if result:
            upload_status[upload_id]['status'] = 'completed'
            upload_status[upload_id]['video_url'] = result
            upload_status[upload_id]['message'] = 'Upload completed successfully'
            upload_status[upload_id]['progress'] = 100
        else:
            upload_status[upload_id]['status'] = 'failed'
            upload_status[upload_id]['message'] = 'Upload failed - no video URL returned'
            upload_status[upload_id]['progress'] = 0
            
    except Exception as e:
        upload_status[upload_id]['status'] = 'failed'
        upload_status[upload_id]['message'] = f'Upload failed: {str(e)}'
        upload_status[upload_id]['progress'] = 0
        upload_status[upload_id]['error_details'] = traceback.format_exc()
        print(f"Upload error for {upload_id}: {e}")
        print(traceback.format_exc())
    
    finally:
        # Clean up uploaded file after a delay
        def cleanup_file():
            time.sleep(300)  # Wait 5 minutes before cleanup
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                    print(f"Cleaned up file: {video_path}")
            except Exception as e:
                print(f"Failed to cleanup file {video_path}: {e}")
        
        cleanup_thread = threading.Thread(target=cleanup_file)
        cleanup_thread.daemon = True
        cleanup_thread.start()

@app.route('/api/<platform>/upload', methods=['POST'])
def upload_video(platform):
    """Upload video to specified platform"""
    
    # Validate platform
    platform = platform.lower()
    if platform not in ['ok', 'dzen', 'vk']:
        return jsonify({'error': 'Platform must be "ok", "dzen", or "vk"'}), 400
    
    # Check if file is present
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    title = request.form.get('title', '')
    
    # Validate inputs
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'File type not allowed. Supported: mp4, avi, mov, mkv, webm, flv, 3gp'}), 400
    
    try:
        # Generate unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Save file
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_filename = f"{timestamp}_{upload_id[:8]}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        # Initialize status
        upload_status[upload_id] = {
            'status': 'processing',
            'message': 'File uploaded, processing...',
            'platform': platform,
            'filename': filename,
            'title': title,
            'upload_time': datetime.now().isoformat(),
            'progress': 0
        }
        
        # Start background upload
        thread = threading.Thread(
            target=upload_to_platform,
            args=(platform, file_path, upload_id, title)
        )
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'upload_id': upload_id,
            'status': 'processing',
            'message': 'File uploaded successfully, processing started',
            'platform': platform,
            'filename': filename
        }), 202
        
    except Exception as e:
        print(f"Upload error: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/<platform>/status/<upload_id>', methods=['GET'])
def check_status(platform, upload_id):
    """Check upload status for specific platform"""
    
    # Validate platform
    platform = platform.lower()
    if platform not in ['ok', 'dzen', 'vk']:
        return jsonify({'error': 'Platform must be "ok", "dzen", or "vk"'}), 400
    
    if upload_id not in upload_status:
        return jsonify({'error': 'Upload ID not found'}), 404
    
    status_info = upload_status[upload_id].copy()
    
    # Verify the upload belongs to the requested platform
    if status_info.get('platform') != platform:
        return jsonify({'error': 'Upload ID does not match platform'}), 400
    
    # Clean up old completed/failed uploads (after 24 hours)
    if status_info['status'] in ['completed', 'failed']:
        upload_time = datetime.fromisoformat(status_info['upload_time'])
        if (datetime.now() - upload_time).total_seconds() > 86400:  # 24 hours
            del upload_status[upload_id]
    
    return jsonify(status_info)

@app.route('/api/status', methods=['GET'])
def get_all_status():
    """Get status of all uploads"""
    return jsonify({
        'uploads': upload_status,
        'total_uploads': len(upload_status)
    })

@app.route('/api/platforms', methods=['GET'])
def get_platforms():
    """Get available platforms"""
    return jsonify({
        'platforms': [
            {
                'name': 'ok', 
                'display_name': 'OK.ru',
                'description': 'Russian social network video platform'
            },
            {
                'name': 'dzen', 
                'display_name': 'Yandex Zen',
                'description': 'Yandex content platform'
            },
            {
                'name': 'vk', 
                'display_name': 'VK Video',
                'description': 'VKontakte video platform'
            }
        ]
    })

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'upload_folder': app.config['UPLOAD_FOLDER'],
        'max_file_size_gb': app.config['MAX_CONTENT_LENGTH'] // (1024 * 1024 * 1024),
        'supported_formats': list(ALLOWED_EXTENSIONS),
        'active_uploads': len([u for u in upload_status.values() if u['status'] in ['processing', 'uploading']])
    })

@app.route('/', methods=['GET'])
def home():
    """Simple home page with API documentation"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Video Upload API</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
            .method { color: #fff; padding: 3px 8px; border-radius: 3px; font-size: 12px; }
            .post { background: #49cc90; }
            .get { background: #61affe; }
            code { background: #f5f5f5; padding: 2px 4px; border-radius: 3px; }
            .platform { background: #e8f4fd; padding: 10px; margin: 5px 0; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>Video Upload API</h1>
        <p>API for uploading videos to OK.ru, Yandex Zen, and VK Video platforms</p>
        
        <h2>Supported Platforms</h2>
        <div class="platform">
            <strong>OK.ru</strong> - Russian social network video platform<br>
            Endpoint: <code>/api/ok/upload</code>
        </div>
        <div class="platform">
            <strong>Yandex Zen</strong> - Yandex content platform<br>
            Endpoint: <code>/api/dzen/upload</code>
        </div>
        <div class="platform">
            <strong>VK Video</strong> - VKontakte video platform<br>
            Endpoint: <code>/api/vk/upload</code>
        </div>
        
        <h2>Endpoints</h2>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/api/{platform}/upload</code>
            <p>Upload video to platform (ok, dzen, or vk). Requires form-data with 'file' and optional 'title'.</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/api/{platform}/status/{upload_id}</code>
            <p>Check upload status by upload ID.</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/api/platforms</code>
            <p>Get list of available platforms.</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/api/health</code>
            <p>Health check and system info.</p>
        </div>
        
        <h2>Usage Examples</h2>
        <pre>
# Upload video to VK Video
curl -X POST -F 'file=@video.mp4' -F 'title=My Video' http://localhost:5000/api/vk/upload

# Upload video to OK.ru
curl -X POST -F 'file=@video.mp4' -F 'title=My Video' http://localhost:5000/api/ok/upload

# Upload video to Yandex Zen
curl -X POST -F 'file=@video.mp4' -F 'title=My Video' http://localhost:5000/api/dzen/upload

# Check status
curl http://localhost:5000/api/vk/status/{upload_id}
        </pre>
        
        <h2>File Requirements</h2>
        <ul>
            <li>Maximum file size: 20GB</li>
            <li>Supported formats: mp4, avi, mov, mkv, webm, flv, 3gp</li>
            <li>Title parameter is optional but recommended</li>
        </ul>
    </body>
    </html>
    """
    return html

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large. Maximum size is 20GB'}), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    print("Starting Video Upload API Server...")
    print("Available platforms: OK.ru, Yandex Zen, VK Video")
    print("Max file size: 20GB")
    print("Supported formats:", ', '.join(ALLOWED_EXTENSIONS))
    app.run(host='0.0.0.0', port=5000, debug=True)