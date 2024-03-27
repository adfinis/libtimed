#!/usr/bin/env python

import time

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

r = client.activities.start(attributes={"comment": "Made with libtimed!"})
print(r.json())
time.sleep(7)
r = client.activities.stop()
print(r.json())
