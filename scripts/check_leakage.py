"""Verifie qu'aucun document utilise comme BASE des datasets synthetiques (cin, residence,
stat) n'est present dans data/kyc/val (meme fichier, meme document ou quasi-doublon).

Bases lues dans les manifest.csv de elt/resultas_quality/<cat> (+ elt/cin_faceswap pour
les modeles de visage). Comparaison par dHash 16x16 (distance de Hamming <= --dist sur 256).

Usage:
    python -m scripts.check_leakage [--dist 24] [--src elt/resultas_quality]
Code retour 1 si une fuite est trouvee.
"""
import argparse
import csv
import os
import re
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'elt'))
import gen_test_data as gt  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VAL = os.path.join(ROOT, 'data', 'kyc', 'val')
SYNTH = re.compile(r'^\d{4}_')


def dhash(img_rgb, size=16):
    g = np.asarray(Image.fromarray(img_rgb).convert('L').resize((size + 1, size)), np.float32)
    return (g[:, 1:] > g[:, :-1]).flatten()


def load_hash(path):
    if path.lower().endswith('.pdf') or path.lower().endswith('.webp'):
        img = gt._load(path, 0)[:, :, ::-1]
    else:
        img = np.asarray(Image.open(path).convert('RGB'))
    return dhash(img)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dist', type=int, default=24)
    p.add_argument('--src', default=os.path.join(ROOT, 'elt', 'resultas_quality'))
    a = p.parse_args()

    bad = 0
    for cat in ('cin', 'residence', 'stat'):
        bases = set()
        mf = os.path.join(a.src, cat, 'manifest.csv')
        for r in csv.DictReader(open(mf, encoding='utf-8')):
            for ph in r['photos'].split('|'):
                if ph:
                    bases.add(os.path.join(ROOT, ph))
        if cat == 'cin':                    # modeles de visage des recto remplaces
            fs = os.path.join(ROOT, 'elt', 'cin_faceswap')
            for sub in ('singles', 'composites'):
                m2 = os.path.join(fs, sub, 'manifest.csv')
                if os.path.exists(m2):
                    for r in csv.DictReader(open(m2, encoding='utf-8')):
                        bases.add(os.path.join(ROOT, 'data', 'kyc', 'train', 'cin', r['template']))
        if cat == 'stat':                   # cartes decoupees -> fichiers train d'origine
            d = os.path.join(ROOT, 'data', 'kyc', 'train', 'stat')
            cards = os.listdir(os.path.join(ROOT, 'elt', 'stat_cards'))

            def used(f):                    # fichier reellement decoupe en cartes
                doc = re.sub(r'(_p\d+|_page\d+)?(_-_Copy)?\.[a-z]+$', '', f, flags=re.I)[:40]
                key = re.sub(r'[^A-Za-z0-9]+', '_', doc + '_' + f[-9:-4])
                return any(c.startswith(key) for c in cards)
            bases = {os.path.join(d, f) for f in os.listdir(d)
                     if f.lower().endswith(('.jpg', '.png')) and not SYNTH.match(f) and used(f)}
        bases = {b for b in bases if os.path.exists(b)}

        vdir = os.path.join(VAL, cat)
        vals = [os.path.join(vdir, f) for f in os.listdir(vdir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png')) and not SYNTH.match(f)]
        vh = {v: load_hash(v) for v in vals}
        names = {os.path.basename(v) for v in vals}
        n_bad = 0
        for b in sorted(bases):
            hb = load_hash(b)
            if os.path.basename(b) in names:
                print(f'  FUITE (meme nom) {cat}: {os.path.basename(b)}')
                n_bad += 1
                continue
            close = [(os.path.basename(v), int((hb != h).sum())) for v, h in vh.items()
                     if (hb != h).sum() <= a.dist]
            if close:
                print(f'  FUITE (quasi-doublon) {cat}: {os.path.basename(b)[:50]} ~ {close[:2]}')
                n_bad += 1
        print(f'{cat}: {len(bases)} bases contre {len(vals)} images val -> {n_bad} fuite(s)')
        bad += n_bad
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
