import os
_basedir = os.path.abspath(os.path.dirname(__file__))

DEBUG = True

THREADS_PER_PAGE = 8

# OIDC setup
OIDC_CLIENT_SECRETS = "secrets/client_secrets.json"
OIDC_COOKIE_SECURE = True
OIDC_CALLBACK_ROUTE = "/oidc/callback"
OIDC_SCOPES = ["openid", "email", "profile"]
SECRET_KEY = 'SecretKeyForSessionSigning24'