import os
from dotenv import load_dotenv


load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"


DB_USER = os.getenv('POSTGRES__USER')
DB_PASS = os.getenv('POSTGRES__PASSWORD')
DB_HOST = os.getenv('POSTGRES__HOST')
DB_PORT = os.getenv('POSTGRES__PORT')
DB_NAME = os.getenv('POSTGRES__DB')
