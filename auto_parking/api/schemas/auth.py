from auto_parking.api.schemas.base import ApiSchema


class LoginRequest(ApiSchema):
    username: str
    password: str


class TokenResponse(ApiSchema):
    access_token: str
    token_type: str = "bearer"
