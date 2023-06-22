#!/usr/bin/env python

import http.server
import webbrowser
from urllib.parse import urlparse

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
        self.wfile.write(b"<html><body><h1>Authentication successful.</h1>You may close this window now.<script>window.close();</script></body></html>")

    # disable logging as it is too verbose
    def log_message(self, format, *args):
        _ = format
        _ = args
        pass



class OIDCClient:
    def __init__(self, client_id, authorization_endpoint, token_endpoint, auth_path):
        self.client_id = client_id
        self.authorization_endpoint = authorization_endpoint
        self.token_endpoint = token_endpoint
        self.auth_path = auth_path

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

    def authorize(self):
        if self.start_browser_flow():
            return self.get_token()
        else:
            return False
