"""Routes navigateur : formulaire d'upload + page de résultats."""
import os

from flask import Blueprint, current_app, jsonify, redirect, render_template, request

from image_utils import load_class_names
from services import retrain_runner
from services.prediction import REJECT_CLASS, predict_document
from services.uploads import allowed_file, save_upload

web_bp = Blueprint('web', __name__)


def _document_classes():
    return [c for c in load_class_names() if c != REJECT_CLASS]


@web_bp.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '' or not allowed_file(file.filename):
            return redirect(request.url)

        target_class = request.form.get('target_class') or None

        filepath = save_upload(file, current_app.config['UPLOAD_FOLDER'])
        try:
            results = predict_document(filepath, target_class)
        finally:
            os.remove(filepath)  # documents KYC sensibles : ne pas les conserver
        return render_template('results.html', results=results)

    return render_template('index.html', classes=_document_classes())


@web_bp.route('/results')
def results():
    return render_template('results.html')


@web_bp.route('/retrain', methods=['POST'])
def retrain():
    # Bouton "Rafraîchir le modèle" de l'UI : pas de jeton (même niveau de confiance
    # que le reste de l'UI web, qui n'a pas d'auth). Sync papi + retrain + déploie.
    payload, code = retrain_runner.start(cwd=current_app.root_path)
    return jsonify(payload), code
