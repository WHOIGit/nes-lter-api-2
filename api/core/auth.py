from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed
from ninja.errors import HttpError


class TokenAuthenticator:
    def __init__(self):
        self.auth = TokenAuthentication()

    def __call__(self, request):
        try:
            user = self.auth.authenticate(request)
            if user is None:
                raise AuthenticationFailed('Unauthorized')
            return user
        except AuthenticationFailed:
            raise HttpError(401, 'Unauthorized')
