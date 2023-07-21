#!/usr/bin/env python

import base64
import datetime
import http.server
import json
import webbrowser
from urllib.parse import urlparse

import keyring
import requests


class OIDCHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        url_path = self.path
        # get the "code" parameter from the query string
        try:
            OIDCHTTPRequestHandler.code = urlparse(url_path).query.split("=")[2]
        except IndexError:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization failed.</h1></body></html>"
            )
            return
        # send the response
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Authentication successful.</h1>You may close this window now.<script>window.close();</script></body></html>"
        )

    # disable logging as it is too verbose
    def log_message(self, *args, **kwargs):
        pass


class OIDCClient:
    def __init__(self, client_id, sso_url, sso_realm, auth_path):
        self.client_id = client_id
        self.sso_url = sso_url
        self.sso_realm = sso_realm
        self.auth_path = auth_path

    def autoconfig(self):
        data = requests.get(
            f"{self.sso_url}/auth/realms/{self.sso_realm}/.well-known/openid-configuration"
        ).json()
        self.authorization_endpoint = data["authorization_endpoint"]
        self.token_endpoint = data["token_endpoint"]

    def start_browser_flow(self):
        # construct the authorization request
        auth_url = f"{self.authorization_endpoint}?client_id={self.client_id}&response_type=code&scope=openid&redirect_uri=http://localhost:5000/{self.auth_path}"
        # start a temporary web server
        server = http.server.HTTPServer(("localhost", 5000), OIDCHTTPRequestHandler)
        # open the browser to the authorization URL
        webbrowser.open_new(auth_url)
        # wait for the authorization response
        # check for is_authorized
        while not server.RequestHandlerClass.code:
            server.handle_request()

        # get the authorization code
        code = server.RequestHandlerClass.code
        # close the temporary web server
        server.server_close()

        self.code = code
        return True

    def get_token(self):
        # construct the token request
        token_request = {
            "code": self.code,
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:5000/" + self.auth_path,
        }
        # send the token request
        token_response = requests.post(self.token_endpoint, data=token_request)
        # check for errors
        if token_response.status_code != 200:
            print(f"Error: {token_response.status_code} {token_response.reason}")
            print(token_response.text)
            return False
        # get the access token
        token = token_response.json()["access_token"]
        return token

    def check_expired(self, token):
        # decode the token
        token_parts = token.split(".")[1]
        # Add padding
        token_parts += "=" * ((4 - len(token_parts) % 4) % 4)
        # Convet to bytes
        token_bytes = token_parts.encode("ascii")
        # base64 decode + utf-8 decode
        token_json = base64.b64decode(token_bytes).decode("utf-8")
        # json to dict
        token_dict = json.loads(token_json)
        # get the expiration time
        expires_at = token_dict["exp"]
        # get the current time
        now = datetime.datetime.now()
        # check if the token is expired
        return now.timestamp() < expires_at

    def keyring_get(self):
        return keyring.get_password("system", "libtimed_token_" + self.client_id)

    def keyring_set(self, token):
        keyring.set_password("system", "libtimed_token_" + self.client_id, token)

    def authorize(self):
        cached_token = self.keyring_get()
        if cached_token:
            if self.check_expired(cached_token):
                return cached_token

        self.autoconfig()
        if self.start_browser_flow():
            token = self.get_token()
            if not token:
                return False
            self.keyring_set(token)
            return token
        else:
            return False
