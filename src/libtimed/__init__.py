from inspect import isclass

import requests
import requests_cache

from libtimed import models


class TimedAPIClient:
    def __init__(self, token, url, api_namespace):
        self.token = token
        self.url = f"{url}/{api_namespace}/"
        self.session = requests.Session()
        self.session.headers["Authorization"] = f"Bearer {token}"
        self.session.headers["Content-Type"] = "application/vnd.api+json"
        self.cached_session = requests_cache.CachedSession(
            "libtimed", expire_after=60 * 60 * 24, use_cache_dir=True
        )
        self.cached_session.headers["Authorization"] = f"Bearer {token}"
        self.cached_session.headers["Content-Type"] = "application/vnd.api+json"
        # Models
        self.users = models.Users(self)
        self.reports = models.Reports(self)
        self.overtime = models.WorktimeBalances(self)
        self.activities = models.Activities(self)
        self.customers = models.Customers(self)
        self.tasks = models.Tasks(self)
        self.projects = models.Projects(self)
        # self.employments = models.Employments(self)

        self._type_map = {
            getattr(models, model).resource_name: getattr(models, model)
            for model in dir(models)
            if isclass(getattr(models, model))
            and issubclass(getattr(models, model), models.BaseModel)
        }
