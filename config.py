import os


class Config:
    UPLOAD_FOLDER = 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # limite de taille de fichier (16 Mo)
    RELOAD_TOKEN = os.environ.get('RELOAD_TOKEN')
