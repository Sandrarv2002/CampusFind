
import os
from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv(override=True)

class Config:
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "development-only-change-this"
    )

    SQLALCHEMY_DATABASE_URI = URL.create(
        drivername="mysql+pymysql",
        username=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        database=os.getenv("DB_NAME", "campusfind_db"),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
