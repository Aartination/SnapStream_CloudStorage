import os
import boto3
AWS_BUCKET_NAME = "snapstream-media-nitin"   # put YOUR bucket name here
AWS_REGION = "ap-south-1"
import uuid
from boto3.dynamodb.conditions import Attr
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify, flash
from werkzeug.utils import secure_filename


# Initialize S3 client
s3_client = boto3.client('s3', region_name=AWS_REGION)
app = Flask(__name__)

# SNS Configuration
SNS_TOPIC_ARN = "arn:aws:sns:ap-south-1:303983719037:snapstream-upload-topic"

sns = boto3.client("sns", region_name=AWS_REGION)

# DynamoDB Configuration
dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
table = dynamodb.Table("SnapStreamMedia")

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov', 'mp3', 'wav', 'ogg'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Create uploads folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory storage for file metadata
# media_metadata = []


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_type(filename):
    """Determine file type category"""
    ext = filename.rsplit('.', 1)[1].lower()
    if ext in {'png', 'jpg', 'jpeg', 'gif'}:
        return 'image'
    elif ext in {'mp4', 'avi', 'mov'}:
        return 'video'
    elif ext in {'mp3', 'wav', 'ogg'}:
        return 'audio'
    return 'unknown'


def format_file_size(size_bytes):
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


@app.route('/')
def index():
    """Render upload page"""
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload_file():
    if "file" not in request.files:
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({'success': False, 'message': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = file.filename

        try:
            # Reset file pointer to beginning
            file.seek(0)
            
            # Determine MIME type
            mime_types = {
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'mp4': 'video/mp4',
                'avi': 'video/x-msvideo',
                'mov': 'video/quicktime',
                'mp3': 'audio/mpeg',
                'wav': 'audio/wav',
                'ogg': 'audio/ogg'
            }
            
            file_ext = filename.rsplit('.', 1)[1].lower()
            content_type = mime_types.get(file_ext, 'application/octet-stream')
            
            # Upload to S3 with Content-Type
            print(f"[DEBUG] Uploading {filename} to S3 bucket: {AWS_BUCKET_NAME}")
            s3_client.upload_fileobj(
                file,
                AWS_BUCKET_NAME,
                filename,
                ExtraArgs={'ContentType': content_type}
            )
            
            # Generate S3 public URL
            file_url = f"https://{AWS_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{filename}"


            file_type = filename.rsplit(".", 1)[1].upper()
            upload_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Generate unique ID
            media_id = str(uuid.uuid4())

            # Save metadata to DynamoDB
            table.put_item(
                Item={
                    "media_id": media_id,
                    "filename": filename,
                    "filetype": file_type,
                    "url": file_url,
                    "upload_time": upload_time
                }
            )

            # Send SNS notification email
            message = f"""
SnapStream Notification 📢

New media uploaded successfully!

File Name: {filename}
File Type: {file_type}
Upload Time: {upload_time}

You can view it in the SnapStream gallery.
"""

            sns.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="SnapStream - New Media Uploaded",
                Message=message
            )

            print("[SNS] Email notification sent")

            print(f"✅ [S3 UPLOAD] {filename} uploaded successfully")
            print(f"   📍 URL: {file_url}")
            print(f"[DYNAMODB] Metadata saved for {filename} with ID: {media_id}")

            return jsonify({
                'success': True, 
                'message': 'File uploaded to AWS S3 & metadata saved to DynamoDB!',
                'data': {
                    'media_id': media_id,
                    'filename': filename,
                    'filetype': file_type,
                    'url': file_url,
                    'upload_time': upload_time
                }
            }), 200

        except Exception as e:
            error_msg = str(e)
            print(f"❌ [ERROR] Upload failed for {filename}")
            print(f"   Error details: {error_msg}")
            
            return jsonify({
                'success': False, 
                'message': f'Upload failed: {error_msg}'
            }), 500

    else:
        return jsonify({
            'success': False, 
            'message': 'Invalid file type! Allowed: jpg, png, mp4, mp3, wav'
        }), 400


@app.route('/gallery')
def gallery():
    """Display gallery of uploaded media (load from DynamoDB)"""
    try:
        response = table.scan()
        media_items = response.get("Items", [])
        # Ensure upload_time exists and sort newest first
        media_items.sort(key=lambda x: x.get("upload_time", ""), reverse=True)
        return render_template('gallery.html', media_files=media_items)

    except Exception as e:
        print("DynamoDB error:", e)
        flash("Could not load media from database.")
        return redirect(url_for("index"))


@app.route('/media/<filename>')
def serve_media(filename):
    """Serve uploaded media files"""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/download/<filename>')
def download_file(filename):
    """Generate presigned URL with download headers for S3 file"""
    try:
        # Extract just the filename (remove any path components for safety)
        safe_filename = filename.split('/')[-1]
        
        # Generate presigned URL with Content-Disposition header for download
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': AWS_BUCKET_NAME,
                'Key': safe_filename,
                'ResponseContentDisposition': f'attachment; filename="{safe_filename}"'
            },
            ExpiresIn=3600  # URL valid for 1 hour
        )
        
        return redirect(presigned_url)
    
    except Exception as e:
        print(f"Download error: {e}")
        return jsonify({'success': False, 'message': f'Download failed: {e}'}), 500

@app.route('/api/media')
def get_media_list():
    """API endpoint to get list of media files"""
    # return jsonify({'files': media_metadata, 'count': len(media_metadata)})


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    print(f"❌ ERROR: File too large (max 100MB)")
    return jsonify({'success': False, 'message': 'File too large. Maximum size is 100MB'}), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'success': False, 'message': 'Resource not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    print(f"❌ ERROR: Internal server error - {str(error)}")
    return jsonify({'success': False, 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SnapStream Media Platform - Starting Server")
    print("=" * 60)
    print(f"📂 Upload folder: {UPLOAD_FOLDER}")
    print(f"✅ Allowed formats: {', '.join(ALLOWED_EXTENSIONS)}")
    print(f"📏 Max file size: {MAX_FILE_SIZE // (1024*1024)}MB")
    print("=" * 60)
    print("🌐 Server running at: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)