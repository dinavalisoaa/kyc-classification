"""Nettoie les jeux reels cin / residence / stat avant regeneration des datasets :

  1. met en quarantaine (deplace, ne supprime pas) les fichiers dont le contenu n'est
     pas de la bonne classe (passeports dans cin, bordereau bancaire dans residence,
     carte fiscale dans stat, fichiers parasites...) -> data/quarantine_noise/<split>/<classe>/
  2. cin : deplace de val vers train les documents servant de MODELES (recto net) et de
     versos pour la generation synthetique, pour qu'aucun modele ne soit aussi dans val ;
  3. retire les composites synthetiques de cin/stat/residence (train) et de stat (val) :
     val devient 100 % reel. Sauvegarde dans data/backup_*.

Tous les deplacements sont traces dans data/clean_real_sets_moves.csv (--undo pour revenir).
Les fichiers absents sont ignores (les donnees ont pu etre nettoyees a la main).

Usage:
    python -m scripts.clean_real_sets --dry-run
    python -m scripts.clean_real_sets
    python -m scripts.clean_real_sets --undo
"""
import argparse
import csv
import os
import re
import shutil
import unicodedata

KYC = 'data/kyc'
LOG = 'data/clean_real_sets_moves.csv'
SYNTH = re.compile(r'^\d{4}_')
IMG = ('.jpg', '.jpeg', '.png', '.webp')


def norm(s):
    return unicodedata.normalize('NFC', s)


# (split, classe) -> prefixes de noms de fichiers a mettre en quarantaine
NOISE = {
    ('val', 'cin'): ['IMG_20260922_154245',            # certificat de residence
                     'Passeport_Thimothee_HOUNDJO',    # passeport du Benin
                     'images__2__',                    # passeport specimen Nouvelle-Zelande
                     'manifest.csv'],
    ('val', 'residence'): ['RESIDENCE-14.jpg',         # bordereau Bank of Africa
                           'RESIDENCE-21_'],           # decret (texte juridique)
    ('train', 'residence'): ['RESIDENCE-20_p1', 'RESIDENCE-20_p2',   # registre commerce / carte fiscale
                             'Carte_r'],                # carte de resident (avec photo)
    ('val', 'stat'): ['Capture_d_écran_2026-09-17_à_15_25_16'],     # certificat INSTAT A4
    ('train', 'stat'): ['CARTE_STATISTIQUE_compressed_'],           # filtre par suffixe ci-dessous
    ('train', 'photo'): ['resize_50.py'],
}
# stat train : seules les pages fiscales (teal 2026) de ce PDF sont du bruit
STAT_TRAIN_NOISE_SUFFIX = ('_p1.jpg', '_page002.jpg')

# CIN : modeles (recto net) + versos utilises pour la synthese : val -> train
CIN_TO_TRAIN = ['CIN-0.jpg', 'CIN-10.jpg', 'CIN-15.jpg', 'CIN-16.jpg', 'CIN-17.jpg',
                'CIN-19.jpg', 'CIN-31.jpg', 'CIN-36.jpg', 'CIN-4.jpg', 'CIN-6.jpg',
                'CIN-7.jpg', 'CIN-9.jpg', 'CIN_2_0_', 'CIN_FANIRIANTSOA_']


def plan():
    moves = []   # (src, dst)

    def add(src_dir, name, dst_dir):
        moves.append((os.path.join(src_dir, name), os.path.join(dst_dir, name)))

    for (split, cls), prefixes in NOISE.items():
        d = os.path.join(KYC, split, cls)
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            nf = norm(f)
            hit = any(nf.startswith(norm(p)) for p in prefixes)
            if hit and (split, cls) == ('train', 'stat'):
                hit = nf.endswith(STAT_TRAIN_NOISE_SUFFIX)
            if hit:
                add(d, f, os.path.join('data/quarantine_noise', split, cls))

    d = os.path.join(KYC, 'val', 'cin')
    for f in sorted(os.listdir(d)):
        if any(f == p or (p.endswith('_') and f.startswith(p)) for p in CIN_TO_TRAIN):
            add(d, f, os.path.join(KYC, 'train', 'cin'))

    for cls in ('cin', 'stat', 'residence'):
        d = os.path.join(KYC, 'train', cls)
        for f in sorted(os.listdir(d)):
            if SYNTH.match(f) or f == 'manifest.csv':
                add(d, f, os.path.join('data/backup_train_synth_photoize', cls))
    d = os.path.join(KYC, 'val', 'stat')
    for f in sorted(os.listdir(d)):
        if SYNTH.match(f):
            add(d, f, 'data/backup_val_stat_synth')

    seen, out = set(), []
    for s, t in moves:
        if s not in seen and os.path.exists(s):
            seen.add(s)
            out.append((s, t))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--undo', action='store_true')
    a = p.parse_args()

    if a.undo:
        with open(LOG, encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        for r in rows:
            os.makedirs(os.path.dirname(r['src']), exist_ok=True)
            shutil.move(r['dst'], r['src'])
        os.remove(LOG)
        print(f'{len(rows)} fichiers remis en place.')
        return

    if os.path.exists(LOG) and not a.dry_run:
        raise SystemExit(f'{LOG} existe deja : deja applique (utiliser --undo).')
    moves = plan()
    by = {}
    for s, t in moves:
        key = os.path.dirname(t).replace('\\', '/')
        by[key] = by.get(key, 0) + 1
    for k, n in sorted(by.items()):
        print(f'{n:5d} -> {k}')
    if a.dry_run:
        return
    for s, t in moves:
        if os.path.exists(t):
            raise SystemExit(f'collision : {t}')
    for s, t in moves:
        os.makedirs(os.path.dirname(t), exist_ok=True)
        shutil.move(s, t)
    with open(LOG, 'w', newline='', encoding='utf-8') as fh:
        w = csv.writer(fh)
        w.writerow(['src', 'dst'])
        w.writerows(moves)
    print(f'{len(moves)} fichiers deplaces ({LOG})')


if __name__ == '__main__':
    main()
