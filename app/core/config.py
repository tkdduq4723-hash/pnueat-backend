from dotenv import load_dotenv
import os

load_dotenv()

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
KAKAO_API_KEY = os.getenv("KAKAO_API_KEY", "")

PNU_LAT = 35.2323
PNU_LNG = 129.0847

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
