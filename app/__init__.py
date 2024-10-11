from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import sys
import os
from dotenv import load_dotenv 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import Config
from app.routes import init_routes 
from flask_migrate import Migrate
from app.models.models import db

migrate = Migrate()

def create_app(config_class=Config):
    # Create the Flask app
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Setup logging
    config_class.setup_logging()

    # Database initialization
    db.init_app(app)

    migrate.init_app(app, db)

    # Initialize routes
    init_routes(app)

    return app
