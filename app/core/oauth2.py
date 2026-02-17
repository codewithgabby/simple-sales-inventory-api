from fastapi.security import OAuth2PasswordBearer

# This tells FastAPI how to extract token from Authorization header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
