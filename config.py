import os
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

THREADS_PER_PAGE = 8

# OIDC setup
CONF_URL = 'https://auth.cern.ch/auth/realms/cern/.well-known/openid-configuration'
LOGOUT_URL = 'https://auth.cern.ch/auth/realms/cern/protocol/openid-connect/logout'
OIDC_CLIENT_SECRETS = "secrets/client_secrets.json"
OIDC_COOKIE_SECURE = True
OIDC_CALLBACK_ROUTE = "/oidc/callback"
OIDC_SCOPES = ["openid", "email", "profile"]
SECRET_KEY = b'S\x9f\x92=\xf5\x1b\xa3\xc3o\x05\x11\x9a\xd1\x0cCb\x82?u+eN\xf8\xbf'
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = True