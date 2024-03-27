#!/usr/bin/env python

from libtimed import TimedAPIClient
from libtimed.oidc import OIDCClient

# API stuff
URL = "https://timed.example.com"
API_NAMESPACE = "api/v1"

# Auth stuff
CLIENT_ID = "timed-client-id"
AUTH_ENDPOINT = "https://sso.example.com/auth/realms/example/protocol/openid-connect/auth"
TOKEN_ENDPOINT = "https://sso.example.com/auth/realms/example/protocol/openid-connect/token"
AUTH_PATH = "timedctl/auth"

oidc_client = OIDCClient(CLIENT_ID, AUTH_ENDPOINT, TOKEN_ENDPOINT, AUTH_PATH)
token = oidc_client.authorize()
client = TimedAPIClient(token, URL, API_NAMESPACE)

time = client.overtime.get()
total_hours = time.total_seconds() / 3600
print(f"{total_hours:.1f}h")
