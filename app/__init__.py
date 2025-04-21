from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask import Flask
import sys
import os
from dotenv import load_dotenv 

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# from app.routes import init_routes 
from flask_migrate import Migrate
from app.models.models import db
from config import Config

migrate = Migrate()

def create_app(config_class=Config):

    app = Flask(__name__)
    app.config.from_object(config_class)

    config_class.setup_logging()

    db.init_app(app)
    migrate.init_app(app, db)

    from app.routes.audio_routes import audio_bp
    from app.routes.entry_routes import entry_bp
    from app.routes.prompts_routes import prompt_bp
    from app.routes.podcast_routes import podcast_bp

    CORS(app, resources={r"/*": {"origins": "http://localhost:3001"}})

    app.register_blueprint(audio_bp)
    app.register_blueprint(entry_bp)
    app.register_blueprint(prompt_bp)
    app.register_blueprint(podcast_bp)

    @app.route('/')
    def home():
        return "Welcome to StoryLine!"

    return app
