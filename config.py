import os
from dotenv import load_dotenv
import logging
import logging.handlers

# Load environment variables from the .env file
load_dotenv()

# Define the base directory where the app will be located
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    # Email and API credentials
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    OPENAI_API_KEY = 'ollama' #| os.getenv('OPENAI_API_KEY')

    # Database Configuration
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
    TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')

    #Eleven labs Configuration
    ELEVEN_LABS_API_KEY = os.getenv('ELEVEN_LABS_API_KEY')

    #Eleven labs Configuration
    NOTEBOOKLM_API_KEY = os.getenv('NOTEBOOKLM_API_KEY')

    # Logging Configuration
    @staticmethod
    def setup_logging():
        """Sets up logging with daily log rotation and UTF-8 encoding."""
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)

        log_directory = os.path.join(basedir, 'logs')
        if not os.path.exists(log_directory):
            os.makedirs(log_directory)

        formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')

        # TimedRotatingFileHandler for rotating the logs daily at midnight, keeping 10 backups
        handler = logging.handlers.TimedRotatingFileHandler(
            os.path.join(log_directory, "JournalAI.log"),
            when="midnight",
            interval=1,
            backupCount=10,
            encoding='utf-8'  # Ensure logs are written with utf-8 encoding
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Log the initialization
        logger.info("Logging setup complete with daily rotation and UTF-8 encoding.")