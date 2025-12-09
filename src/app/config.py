import os

class BaseConfig:
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 8 * 1024 * 1024))
    DB_NAME = os.getenv("DB_NAME", "app.db")

class DevConfig(BaseConfig):
    DEBUG = True
