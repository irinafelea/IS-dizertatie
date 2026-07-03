from dotenv import load_dotenv
import os

load_dotenv()

BASE_URL = os.getenv("SERVER_BASE_URL")
API_URL = os.getenv("SERVER_API_URL")
TOKEN = os.getenv("SERVER_TOKEN")
DOMAIN_ID = os.getenv("SERVER_DOMAIN_ID")
SEMESTER_ID = os.getenv("SERVER_SEMESTER_ID")
ALLOWED_ORIGIN = os.getenv("ALLOWED_ORIGIN")