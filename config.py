import os
from dotenv import load_dotenv




load_dotenv()
class Config:

    # ============================================================
    # SECURITY
    # ============================================================
    SECRET_KEY = os.environ.get("SECRET_KEY") or "agromart-secret-key"

    # ============================================================
    # DATABASE
    # ============================================================
    SQLALCHEMY_DATABASE_URI = "sqlite:///agromart.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


    # ============================================================
    # FORMS / CSRF
    # ============================================================

    WTF_CSRF_ENABLED = True


    # ============================================================
    # FILE UPLOADS
    # ============================================================
    UPLOAD_FOLDER = os.path.join("app", "static", "uploads", "products")
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024


    # ============================================================
    # EMAIL CONFIGURATION
    # ============================================================

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = (os.environ.get("MAIL_USE_TLS", "true").lower()== "true")
    MAIL_USE_SSL = (os.environ.get("MAIL_USE_SSL", "false").lower()== "true")
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER")