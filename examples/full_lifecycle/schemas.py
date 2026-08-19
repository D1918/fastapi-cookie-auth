from pydantic import BaseModel


class CSRFToken(BaseModel):
    csrf_token: str


class WebAuthTokenData(CSRFToken):
    access_token: str
    refresh_token: str
