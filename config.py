from datetime import timedelta

DEBUG = True
SECRET_KEY = 'IoTLab'
SESSION_PERMANENT = False
SESSION_TYPE = 'filesystem'
SQLALCHEMY_DATABASE_URI= 'sqlite:///sessions.sqlite3'
PERMANENT_SESSION_LIFETIME = timedelta(days=1)