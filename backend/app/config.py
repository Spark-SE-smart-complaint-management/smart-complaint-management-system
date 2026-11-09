import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./scms.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
JWT_ALGORITHM = "HS256"
# REQ-3: token validity is configurable
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
