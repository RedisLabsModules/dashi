from flask import Flask
from flask_marshmallow import Marshmallow
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
import logging
from .config import Config

db = SQLAlchemy()
migrate = Migrate()
ma = Marshmallow()


def create_app():
    app = Flask(__name__)
    # Set up the application's logger
    app.logger.setLevel(logging.INFO)

    # Set up a file handler for the logger
    handler = logging.FileHandler("application.log")
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # Add the handler to the logger
    app.logger.addHandler(handler)
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    ma.init_app(app)

    from .routes import main

    app.register_blueprint(main)

    from .commands import sync_db

    app.cli.add_command(sync_db)
    return app
