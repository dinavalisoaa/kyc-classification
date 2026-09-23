import json
import os

import numpy as np
from PIL import Image

IMG_SIZE = 224
CLASSES_FILE = 'class_names.json'
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
PDF_EXTENSIONS = {'.pdf'}
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | PDF_EXTENSIONS


def get_classes_from_data_dir(data_dir='./data/kyc/train'):
    # Class names = training set subfolders, sorted (order used by Keras)
    return sorted(d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d)))


def save_class_names(class_names, filepath=CLASSES_FILE):
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(class_names, f, ensure_ascii=False, indent=2)


def load_class_names(filepath=CLASSES_FILE):
    with open(filepath, encoding='utf-8') as f:
        return json.load(f)


def render_pdf_pages(pdf_path, max_pages=1, zoom=2.0):
    # Renders the first pages of a PDF as PIL images (PyMuPDF)
    import pymupdf as fitz
    pages = []
    with fitz.open(pdf_path) as doc:
        for i in range(min(max_pages, len(doc))):
            pix = doc[i].get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            pages.append(Image.frombytes('RGB', (pix.width, pix.height), pix.samples))
    return pages


def load_pil_image(path):
    # Opens an image or the 1st page of a PDF, as RGB (EXIF orientation applied)
    if os.path.splitext(path)[1].lower() in PDF_EXTENSIONS:
        return render_pdf_pages(path, max_pages=1)[0]
    from PIL import ImageOps
    with Image.open(path) as img:
        return ImageOps.exif_transpose(img).convert('RGB')


def load_and_preprocess_image(path, img_size=IMG_SIZE):
    # Returns a batch (1, H, W, 3), values 0-255: MobileNetV3 normalizes internally
    img = load_pil_image(path).resize((img_size, img_size))
    return np.expand_dims(np.asarray(img, dtype=np.float32), axis=0)
