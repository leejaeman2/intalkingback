from ninja_jwt.authentication import JWTAuth


class TokenVersionJWTAuth(JWTAuth):
    def jwt_authenticate(self, request, token):
        validated_token = self.get_validated_token(token)
        user = self.get_user(validated_token)
        jwt_version = validated_token.payload.get('token_version', None)
        if jwt_version is None or getattr(user, 'token_version', 0) != jwt_version:
            return None
        return user
