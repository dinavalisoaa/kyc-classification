"""Downloads Kaggle datasets and samples a few images into data/externe/<class>/.

Prerequisites: Kaggle account + credentials (~/.kaggle/kaggle.json, or KAGGLE_USERNAME /
KAGGLE_KEY env vars). `pip install kagglehub`.

Usage: python -m scripts.download_kaggle [--max 60]
External images are added to TRAIN only by training/prepare_dataset.py (validation stays
100% real PAPI documents). Check each dataset's license before using it in production.
"""
import argparse
import os
import random

from image_utils import IMAGE_EXTENSIONS, load_pil_image

TARGET_DIR = 'data/externe'
SEED = 42

# Kaggle slug -> target class. Foreign ID documents: generic "identity card" signal only;
# real Malagasy CINs remain the reference for validation.
DATASETS = {
    'chitreshkr/idnet-identity-document-analysis': 'cin',
}


def list_images(root_dir):
    for folder, _, files in os.walk(root_dir):
        for f in files:
            if os.path.splitext(f)[1].lower() in IMAGE_EXTENSIONS:
                yield os.path.join(folder, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--max', type=int, default=60, help="max images per dataset")
    args = parser.parse_args()

    import kagglehub
    rng = random.Random(SEED)
    for slug, label in DATASETS.items():
        print(f'Downloading {slug} ...')
        root_dir = kagglehub.dataset_download(slug)
        images = sorted(list_images(root_dir))
        rng.shuffle(images)
        output_dir = os.path.join(TARGET_DIR, label)
        os.makedirs(output_dir, exist_ok=True)
        n = 0
        for path in images:
            if n >= args.max:
                break
            try:
                load_pil_image(path).save(
                    os.path.join(output_dir, f'{slug.split("/")[-1]}_{n}.jpg'), quality=92)
                n += 1
            except Exception as e:
                print(f'SKIPPED {path}: {e}')
        print(f'{slug}: {n}/{len(images)} images -> {output_dir}')


if __name__ == '__main__':
    main()
