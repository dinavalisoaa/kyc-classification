"""Retrains the model with a quality gate: refuses to replace the production
model.keras if the new version regresses vs. the current one (compared on the SAME
validation set, from this run). Versions every attempt under models/.

Usage:
    python -m training.retrain                # rebuild data/kyc + sync papi -> train -> compare -> deploy if OK
    python -m training.retrain --no-prepare    # skip rebuilding data/kyc from cin-data (already done manually)
    python -m training.retrain --no-sync       # skip syncing new papi documents (PAPI_API_URL)
    python -m training.retrain --force         # deploy even on regression
    python -m training.retrain --tolerance 0.01  # tolerate up to 1pt accuracy regression
"""
import argparse
import json
import os
import shutil
from datetime import datetime

import requests
import tensorflow as tf

from image_utils import IMG_SIZE, load_class_names, save_class_names
from services import papi_sync
from training import model_training as mt
from training import prepare_dataset

MODELS_DIR = 'models'
MODEL_PATH = './model.keras'
CLASSES_PATH = 'class_names.json'
HISTORY_PATH = os.path.join(MODELS_DIR, 'history.json')
BATCH_SIZE = 16
EPOCHS = 30


def timestamp():
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def load_history():
    if os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, encoding='utf-8') as f:
            return json.load(f)
    return []


def save_history(history):
    with open(HISTORY_PATH, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def evaluate_accuracy(model, val_ds):
    _, acc = model.evaluate(val_ds, verbose=0)
    return float(acc)


def notify_app_reload():
    # Tells the Flask service to reload the model that was just deployed.
    # No-op if APP_RELOAD_URL isn't set (manual/non-Docker usage).
    url = os.environ.get('APP_RELOAD_URL')
    if not url:
        return
    try:
        headers = {'X-Reload-Token': os.environ.get('RELOAD_TOKEN', '')}
        resp = requests.post(url, headers=headers, timeout=10)
        print(f'== App reload notification: {resp.status_code} ==')
    except requests.RequestException as e:
        print(f'== App reload notification failed: {e} ==')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-prepare', action='store_true', help="don't rerun training/prepare_dataset.py")
    parser.add_argument('--no-sync', action='store_true', help="don't sync papi documents")
    parser.add_argument('--force', action='store_true', help="deploy even on regression")
    parser.add_argument('--tolerance', type=float, default=0.0,
                        help="accuracy regression tolerated before refusing (default 0.0 = none)")
    args = parser.parse_args()

    if not args.no_prepare:
        print('== Preparing data (cin-data -> data/kyc) ==')
        prepare_dataset.main()

    if not args.no_sync:
        print('== Syncing new documents (papi API) ==')
        papi_sync.sync()

    os.makedirs(MODELS_DIR, exist_ok=True)
    ts = timestamp()

    print('== Loading datasets ==')
    train_ds, val_ds, class_names, class_weight = mt.prepare_datasets(IMG_SIZE, IMG_SIZE, BATCH_SIZE)
    print('Classes:', class_names)

    # Accuracy of the current production model, on this same validation set (reference)
    previous_accuracy = None
    if os.path.exists(MODEL_PATH) and os.path.exists(CLASSES_PATH):
        if load_class_names(CLASSES_PATH) == class_names:
            print('== Evaluating the previous model (reference) ==')
            previous_model = tf.keras.models.load_model(MODEL_PATH)
            previous_accuracy = evaluate_accuracy(previous_model, val_ds)
            print(f'Previous model - validation accuracy: {previous_accuracy:.4f}')
        else:
            print('Classes differ from the last deployed model: comparison skipped.')

    print('== Training ==')
    model = mt.build_model(IMG_SIZE, IMG_SIZE, len(class_names))
    mt.compile_model(model)
    history = mt.train_model(model, train_ds, val_ds, EPOCHS, class_weight)
    new_accuracy = evaluate_accuracy(model, val_ds)
    print(f'New model - validation accuracy: {new_accuracy:.4f}')

    # Versioned save of this attempt, whether it gets deployed or not
    prefix = os.path.join(MODELS_DIR, f'run_{ts}')
    mt.plot_and_save_metrics(history, f'{prefix}_metrics.png')
    mt.evaluate_model(model, val_ds, class_names, f'{prefix}_confusion.png')
    model.save(os.path.join(MODELS_DIR, f'model_{ts}.keras'))

    regression = previous_accuracy is not None and new_accuracy < previous_accuracy - args.tolerance
    should_deploy = args.force or not regression

    if should_deploy:
        if os.path.exists(MODEL_PATH):
            # back up the current production model before overwriting (rollback possible)
            shutil.copy2(MODEL_PATH, os.path.join(MODELS_DIR, f'model_avant_{ts}.keras'))
        model.save(MODEL_PATH)
        save_class_names(class_names, CLASSES_PATH)
        mt.plot_and_save_metrics(history, 'metrics_plot.png')
        mt.evaluate_model(model, val_ds, class_names, 'confusion_matrix.png')
        print(f'== DEPLOYED to prod (model.keras): accuracy {new_accuracy:.4f} ==')
        notify_app_reload()
    else:
        print(f'== REJECTED: regression {previous_accuracy:.4f} -> {new_accuracy:.4f}. '
              f'Model kept at {MODELS_DIR}/model_{ts}.keras for inspection. '
              f'Rerun with --force to deploy anyway. ==')

    history_log = load_history()
    history_log.append({
        'date': ts,
        'classes': class_names,
        'accuracy_ancien': previous_accuracy,
        'accuracy_nouveau': new_accuracy,
        'deploye': should_deploy,
        'force': args.force,
    })
    save_history(history_log)


if __name__ == '__main__':
    main()
