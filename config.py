import os
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SECRET_KEY = os.environ.get("SECRET_KEY", "change-this-development-secret-key")
DATABASE = os.path.join(BASE_DIR, "instance", "nutrition.db")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATASET_PATH = os.path.join(BASE_DIR, "data", "NLP_dataset_500.xlsx")
