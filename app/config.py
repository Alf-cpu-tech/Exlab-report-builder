import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

ALLOWED_EXTENSIONS = {'xls', 'xlsx', 'csv'}

SECRET_KEY = "change_this"

DATABASE_PATH = os.path.join(BASE_DIR, "instance", "app.db")