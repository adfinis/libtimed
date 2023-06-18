import requests

from libtimed import models


class TimedAPIClient:
    def __init__(self, token, url, api_namespace):
        self.token = token
        self.url = f"{url}/{api_namespace}/"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Type"] = "application/vnd.api+json"

        # Models
        self.users: models.Users = models.Users(self)
        self.reports: models.Reports = models.Reports(self)
        self.overtime: models.Overtime = models.Overtime(self)
        # self.projects = models.Projects(self)
        # self.customers = models.Customers(self)
        # self.tasks = models.Tasks(self)
        # self.activities = models.Activities(self)
        # self.employments = models.Employments(self)
