#!/usr/bin/env python

import pyfzf

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
client = TimedAPIClient(token, URL, API_NAMESPACE)

customers = client.customers.get()

customer_name = pyfzf.FzfPrompt().prompt(
    [customer["attributes"]["name"] for customer in customers]
)[0]

if not customer_name:
    exit()

customer = next(
    customer
    for customer in customers
    if customer["attributes"]["name"] == customer_name
)

projects = client.projects.get({"customer": customer["id"]})

project_name = pyfzf.FzfPrompt().prompt(
    [project["attributes"]["name"] for project in projects]
)
if not project_name:
    exit()

project = next(
    project for project in projects if project["attributes"]["name"] == project_name[0]
)
tasks = client.tasks.get({"project": project["id"]})

task_name = pyfzf.FzfPrompt().prompt([task["attributes"]["name"] for task in tasks])

if not task_name:
    exit()

task = next(task for task in tasks if task["attributes"]["name"] == task_name[0])


duration = input("Task duration [HH:MM:SS]: ")

comment = input("Task comment: ")

r = client.reports.post(
    {"duration": duration, "comment": comment}, {"task": task["id"]}
)
if r.status_code == 201:
    print("Report successfully created!")

else:
    print("Error while trying to create report!")
    print(r.json())
