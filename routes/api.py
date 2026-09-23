"""Routes machine-à-machine : classification JSON (backend PAPI), reload modèle,
synchro papi et ré-entraînement à la demande."""
import os

from flask import Blueprint, current_app, jsonify, request

from services import papi_sync, retrain_runner
from services.prediction import load_model, predict_document
from services.uploads import allowed_file, save_upload

api_bp = Blueprint('api', __name__)


def _unauthorized():
    token = current_app.config['RELOAD_TOKEN']
    return not token or request.headers.get('X-Reload-Token') != token


@api_bp.route('/api/classify', methods=['POST'])
def classify():
    file = request.files.get('file')
    if not file or not allowed_file(file.filename):
        return jsonify(error='fichier manquant ou extension non autorisée'), 400

    target_class = request.form.get('target_class') or None

    filepath = save_upload(file, current_app.config['UPLOAD_FOLDER'])
    try:
        return jsonify(predict_document(filepath, target_class))
    finally:
        os.remove(filepath)


@api_bp.route('/internal/reload', methods=['POST'])
def reload_model():
    # Appelé par le service de ré-entraînement après un déploiement réussi :
    # recharge model.keras/class_names.json sans redémarrer le process.
    if _unauthorized():
        return jsonify(error='unauthorized'), 401
    load_model.cache_clear()
    load_model()
    return jsonify(status='reloaded')


@api_bp.route('/internal/sync-papi', methods=['POST'])
def sync_papi_endpoint():
    # Synchro à la demande, en direct (pas de subprocess : léger, retour structuré immédiat).
    if _unauthorized():
        return jsonify(error='unauthorized'), 401
    if retrain_runner.is_running():
        return jsonify(error='retrain en cours : la synchro papi en fait déjà partie'), 409
    if not retrain_runner.sync_lock.acquire(blocking=False):
        return jsonify(error='synchro papi déjà en cours'), 409
    try:
        return jsonify(papi_sync.sync())
    finally:
        retrain_runner.sync_lock.release()


@api_bp.route('/internal/retrain', methods=['POST'])
def retrain():
    # Lance training.retrain en tâche de fond (peut prendre plusieurs minutes) et répond
    # immédiatement. Statut consultable via GET /internal/retrain/status.
    if _unauthorized():
        return jsonify(error='unauthorized'), 401

    body = request.get_json(silent=True) or {}
    tolerance = None
    if 'tolerance' in body:
        try:
            tolerance = float(body['tolerance'])
        except (TypeError, ValueError):
            return jsonify(error='tolerance doit être un nombre'), 400

    payload, code = retrain_runner.start(
        cwd=current_app.root_path,
        no_prepare=bool(body.get('no_prepare')),
        no_sync=bool(body.get('no_sync')),
        force=bool(body.get('force')),
        tolerance=tolerance,
    )
    return jsonify(payload), code


@api_bp.route('/internal/retrain/status', methods=['GET'])
def retrain_status():
    if _unauthorized():
        return jsonify(error='unauthorized'), 401
    return jsonify(retrain_runner.status())
