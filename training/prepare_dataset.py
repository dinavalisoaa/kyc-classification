"""Builds data/kyc/{train,val}/<class>/ from cin-data/ (+ 'autre' rejection class).

- PDFs are rendered as JPG (all pages up to MAX_PAGES).
- The train/val split is done by GROUP (client/file) so that a given piece (e.g. the 6
  pages of one 'statuts' document) doesn't end up split between train and val.
- Idempotent: the data/kyc folder is rebuilt on every run.
"""
import os
import random
import re
import shutil
from collections import defaultdict

from image_utils import ALLOWED_EXTENSIONS, PDF_EXTENSIONS, load_pil_image, render_pdf_pages

SOURCE = 'cin-data'
TARGET_DIR = 'data/kyc'
SEED = 42
VAL_RATIO = 0.2
MAX_PAGES = 3          # max pages rendered per PDF
OTHER_MAX = 120        # max images for the 'autre' rejection class
OTHER_SOURCES = ['data/train/daisy', 'data/train/rose', 'data/train/headphone',
                 'data/train/tulip', 'data/train/sunflower', 'data/train/dandelion']

# cin-data folder -> class. Archives, Autres, Attestation, NIF, RCS: out of scope.
MAPPING = {
    'CIN': 'cin',
    'Photo identite': 'photo',
    'Certificat de residence': 'residence',
    'Statuts': 'statuts',
    'CIF': 'cif',
    'Carte fiscale': 'cif',
    'Carte statistique': 'stat',
}


def group_key_from_filename(filename):
    # '08_3Stratedge_statut (1).jpeg' -> '08_3Stratedge' ; otherwise the name without extension
    m = re.match(r'^(\d{2}_[^_]+)_', filename)
    return m.group(1) if m else os.path.splitext(filename)[0]


def save_image(img, folder, name):
    os.makedirs(folder, exist_ok=True)
    img.save(os.path.join(folder, name + '.jpg'), quality=92)


def export_file(path, folder, prefix):
    ext = os.path.splitext(path)[1].lower()
    n = 0
    if ext in PDF_EXTENSIONS:
        for i, page in enumerate(render_pdf_pages(path, max_pages=MAX_PAGES)):
            save_image(page, folder, f'{prefix}_p{i}')
            n += 1
    else:
        save_image(load_pil_image(path), folder, prefix)
        n = 1
    return n


def collect_sources():
    # class -> {group -> [paths]}
    classes = defaultdict(lambda: defaultdict(list))
    for folder, label in MAPPING.items():
        base = os.path.join(SOURCE, folder)
        for f in sorted(os.listdir(base)):
            if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS:
                classes[label][group_key_from_filename(f)].append(os.path.join(base, f))
    return classes


def split_groups(groups, rng):
    keys = sorted(groups)
    rng.shuffle(keys)
    n_val = max(1, round(len(keys) * VAL_RATIO))
    return keys[n_val:], keys[:n_val]


def main():
    rng = random.Random(SEED)
    shutil.rmtree(TARGET_DIR, ignore_errors=True)
    counts = defaultdict(lambda: {'train': 0, 'val': 0})

    for label, groups in collect_sources().items():
        train_keys, val_keys = split_groups(groups, rng)
        for split, keys in (('train', train_keys), ('val', val_keys)):
            for g in keys:
                for path in groups[g]:
                    try:
                        prefix = re.sub(r'[^\w-]', '_', os.path.splitext(os.path.basename(path))[0])
                        counts[label][split] += export_file(
                            path, os.path.join(TARGET_DIR, split, label), prefix)
                    except Exception as e:
                        print(f'SKIPPED {path}: {e}')

    # 'autre' rejection class: off-topic images already present in the repo
    other_images = [os.path.join(d, f) for d in OTHER_SOURCES if os.path.isdir(d)
              for f in os.listdir(d) if os.path.splitext(f)[1].lower() in ALLOWED_EXTENSIONS]
    rng.shuffle(other_images)
    other_images = other_images[:OTHER_MAX]
    n_val = round(len(other_images) * VAL_RATIO)
    for i, path in enumerate(other_images):
        split = 'val' if i < n_val else 'train'
        try:
            save_image(load_pil_image(path), os.path.join(TARGET_DIR, split, 'autre'), f'autre_{i}')
            counts['autre'][split] += 1
        except Exception as e:
            print(f'SKIPPED {path}: {e}')

    # External images (Kaggle, see scripts/download_kaggle.py): train only
    external_dir = 'data/externe'
    if os.path.isdir(external_dir):
        for label in os.listdir(external_dir):
            folder = os.path.join(external_dir, label)
            for i, f in enumerate(sorted(os.listdir(folder))):
                try:
                    save_image(load_pil_image(os.path.join(folder, f)),
                           os.path.join(TARGET_DIR, 'train', label), f'ext_{i}')
                    counts[label]['train'] += 1
                except Exception as e:
                    print(f'SKIPPED {f}: {e}')

    print(f'{"class":<12}{"train":>7}{"val":>6}')
    for label in sorted(counts):
        print(f'{label:<12}{counts[label]["train"]:>7}{counts[label]["val"]:>6}')


if __name__ == '__main__':
    main()
