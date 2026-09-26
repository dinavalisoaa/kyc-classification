"""Deplace une partie des VRAIES images de validation (cin, stat, residence) vers
train, en decoupant par groupe (un meme document / ses pages ne se retrouvent jamais
des deux cotes). Les images synthetiques (nom '0000_xxx') ne sont pas touchees.

Trace tous les deplacements dans data/split_real_val_moves.csv (retour arriere possible
avec --undo).

Usage:
    python -m scripts.split_real_val                 # 50 % des groupes reels -> train
    python -m scripts.split_real_val --ratio 0.6
    python -m scripts.split_real_val --undo
"""
import argparse
import csv
import os
import random
import re
import shutil
from collections import defaultdict

VAL_DIR = 'data/kyc/val'
TRAIN_DIR = 'data/kyc/train'
LOG = 'data/split_real_val_moves.csv'
CLASSES = ('cin', 'stat', 'residence')
SYNTH = re.compile(r'^\d{4}_')
IMG_EXT = ('.jpg', '.jpeg', '.png', '.webp')


def group_key(name):
    # 'CIN-12_p0.jpg' -> 'CIN-12' ; 'xxx_<sha256>_p1.jpg' -> 'xxx'
    base = re.sub(r'(_p\d+|_page\d+)?\.[a-z]+$', '', name, flags=re.I)
    return re.sub(r'_[0-9a-f]{64}$', '', base)


def split(ratio, seed):
    rng = random.Random(seed)
    moves = []
    for cls in CLASSES:
        folder = os.path.join(VAL_DIR, cls)
        groups = defaultdict(list)
        for f in sorted(os.listdir(folder)):
            if f.lower().endswith(IMG_EXT) and not SYNTH.match(f):
                groups[group_key(f)].append(f)
        keys = sorted(groups)
        rng.shuffle(keys)
        n_train = round(len(keys) * ratio)
        for k in keys[:n_train]:
            for f in groups[k]:
                moves.append((cls, f))
        print(f'{cls}: {len(keys)} groupes reels ({sum(map(len, groups.values()))} images) '
              f'-> {n_train} groupes vers train')
    return moves


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--ratio', type=float, default=0.5)
    p.add_argument('--seed', type=int, default=42)
    p.add_argument('--undo', action='store_true')
    a = p.parse_args()

    if a.undo:
        with open(LOG, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            shutil.move(os.path.join(TRAIN_DIR, r['class'], r['file']),
                        os.path.join(VAL_DIR, r['class'], r['file']))
        os.remove(LOG)
        print(f'{len(rows)} images remises dans val.')
        return

    if os.path.exists(LOG):
        raise SystemExit(f'{LOG} existe deja : deja applique (utiliser --undo).')
    moves = split(a.ratio, a.seed)
    for cls, f in moves:
        dst = os.path.join(TRAIN_DIR, cls, f)
        if os.path.exists(dst):
            raise SystemExit(f'collision : {dst}')
    for cls, f in moves:
        shutil.move(os.path.join(VAL_DIR, cls, f), os.path.join(TRAIN_DIR, cls, f))
    with open(LOG, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['class', 'file'])
        w.writerows(moves)
    print(f'{len(moves)} images deplacees val -> train ({LOG})')


if __name__ == '__main__':
    main()
