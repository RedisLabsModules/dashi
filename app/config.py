from decouple import config

class Config(object):
    SQLALCHEMY_DATABASE_URI = f"postgresql://{config('DB_USER')}:{config('DB_PASSWORD')}@{config('DB_HOST')}:{config('DB_PORT')}/{config('DB_NAME')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TOKEN_SALT = config('TOKEN_SALT', default=None)
