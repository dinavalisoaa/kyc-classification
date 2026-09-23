import os
import uuid

from werkzeug.utils import secure_filename

from image_utils import ALLOWED_EXTENSIONS


def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file, upload_folder):
    # Unique name: avoids overwriting between concurrent requests
    ext = os.path.splitext(secure_filename(file.filename))[1].lower()
    filepath = os.path.join(upload_folder, f'{uuid.uuid4().hex}{ext}')
    file.save(filepath)
    return filepath
