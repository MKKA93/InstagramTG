import os
import jwt
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

# Load secret key and algorithm from environment variables
SECRET_KEY = os.getenv('SECRET_KEY', 'your_secret_key')
ALGORITHM = os.getenv('ALGORITHM', 'HS256')

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Extract the token from the Authorization header
        token = request.headers.get("Authorization")
        if token:
            token = token.split(" ")[1]  # Extract the token from "Bearer <token>"
            try:
                # Decode the token to get the payload
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                request.state.user = payload  # Store user info in request state
            except jwt.ExpiredSignatureError:
                raise HTTPException(status_code=401, detail="Token has expired")
            except jwt.InvalidTokenError:
                raise HTTPException(status_code=401, detail="Invalid token")
        else:
            raise HTTPException(status_code=403, detail="Authorization token is missing")

        # Call the next middleware or endpoint
        response = await call_next(request)
        return response
