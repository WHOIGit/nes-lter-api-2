from ninja.security import HttpBearer
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from ninja.errors import HttpError

class TokenAuthenticator(HttpBearer):
    def __init__(self):
        self.auth = TokenAuthentication()
        super().__init__()  # Make sure to call parent init!

    def authenticate(self, request, token):
        # This ensures the DRF token auth will see the header
        request.META['HTTP_AUTHORIZATION'] = f"Token {token}"
        user_auth_tuple = self.auth.authenticate(request)
        if user_auth_tuple is None:
            raise HttpError(401, 'Unauthorized')
        user, _ = user_auth_tuple
        return user
