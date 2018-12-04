REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 3
LOG_FORMAT_FILE = '[%(asctime)s]\t%(levelname)s\t%(module)s\t%(message)s'
LOG_FORMAT_STREAM = '%(levelname)s\t%(module)s\t%(message)s'
LOG_LEVEL = 10

class Config(object):
    SECRET_KEY = 'key'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Celery
    CELERY_CONFIG_MODULE = 'configs.celeryconfig'

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    DEBUG = True
    TESTING = True

    USER_NAME = "johnsnow"
    USER_PASSWORD = "john"

class DevelopmentConfig(Config):
    DEBUG = True

configs = {
    "production": ProductionConfig,
    "testing": TestingConfig,
    "development": DevelopmentConfig,
}

