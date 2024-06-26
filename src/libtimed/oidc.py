#!/usr/bin/env python

import base64
import datetime
import http.server
import json
import time
import webbrowser
from urllib.parse import parse_qs, urlparse

import keyring
import requests


class OIDCHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
    code = None

    def do_GET(self):  # noqa: N802
        url_path = self.path
        # get the "code" parameter from the query string
        try:
            OIDCHTTPRequestHandler.code = parse_qs(urlparse(url_path).query)["code"][0]
        except IndexError:
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization failed.</h1></body></html>")
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
    def __init__(self, client_id, sso_url, sso_realm, auth_path, use_device_flow=False):
        self.client_id = client_id
        self.sso_url = sso_url
        self.sso_realm = sso_realm
        self.auth_path = auth_path
        self.use_device_flow = use_device_flow

    def autoconfig(self):
        data = requests.get(
            f"{self.sso_url}/realms/{self.sso_realm}/.well-known/openid-configuration"
        ).json()
        self.authorization_endpoint = data["authorization_endpoint"]
        self.token_endpoint = data["token_endpoint"]
        self.device_endpoint = data["device_authorization_endpoint"]

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

    def start_device_flow(self):
        # construct the authorization request
        auth_data = requests.post(self.device_endpoint, data={"client_id": self.client_id}).json()
        verification_uri_complete = auth_data["verification_uri_complete"]
        verification_uri = auth_data["verification_uri"]
        device_code = auth_data["device_code"]
        user_code = auth_data["user_code"]

        # open the browser to the authorization URL
        webbrowser.open_new(verification_uri_complete)
        # print manual instructions
        print(f"Please visit {verification_uri} and enter the code {user_code}")
        time.sleep(5)

        resp = {}
        while "access_token" not in resp:
            resp = requests.post(
                self.token_endpoint,
                data={
                    "client_id": self.client_id,
                    "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                    "device_code": device_code,
                },
            ).json()
            print(resp)
            time.sleep(5)
        return resp["access_token"]

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
            print(f"Error: {token_response.status_code} {token_response.reason}\n")
            print(token_response.text)
            return False
        # get the access token
        return token_response.json()["access_token"]

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
        if cached_token and self.check_expired(cached_token):
            return cached_token

        self.autoconfig()
        if self.use_device_flow:
            if token := self.start_device_flow():
                self.keyring_set(token)
                return token
            return False

        if self.start_browser_flow():
            token = self.get_token()
            if not token:
                return False
            self.keyring_set(token)
            return token
        return False
