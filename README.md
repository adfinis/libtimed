Libtimed
=


A library to interact with the json:api API of [timed](https://github.com/adfinis/timed-backend)

This is work in progress.

## Examples
Get overtime of the current day
```python
from libtimed import TimedAPIClient
from libtimed.oidc import OIDCClient

# API stuff
URL = "https://timed.example.com"
API_NAMESPACE = "api/v1"

# Auth stuff
CLIENT_ID = "timed-client-id"
AUTH_ENDPOINT = (
    "https://sso.example.com/auth/realms/example/protocol/openid-connect/auth"
)
TOKEN_ENDPOINT = (
    "https://sso.example.com/auth/realms/example/protocol/openid-connect/token"
)
AUTH_PATH = "timedctl/auth"

oidc_client = OIDCClient(CLIENT_ID, AUTH_ENDPOINT, TOKEN_ENDPOINT, AUTH_PATH)
token = oidc_client.authorize()
del oidc_client

client = TimedAPIClient(token, URL, API_NAMESPACE)

overtime = client.overtime.get()

print(
    overtime[0]["attributes"]["balance"]
)
```