import os

from flask import Flask

from config import Config
from routes.api import api_bp
from routes.web import web_bp
from services.prediction import load_model


def create_app():
    flask_app = Flask(__name__)
    flask_app.config.from_object(Config)

    flask_app.register_blueprint(web_bp)
    flask_app.register_blueprint(api_bp)

    os.makedirs(flask_app.config['UPLOAD_FOLDER'], exist_ok=True)
    load_model()
    return flask_app


app = create_app()

if __name__ == '__main__':
    app.run()
