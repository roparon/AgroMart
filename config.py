import os


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY") or "agromart-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///agromart.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True