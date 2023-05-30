import requests
import logging
from Credentials import Credentials
from datetime import datetime, timedelta


class Token:
    def __init__(self):
        self.url = "https://osu.ppy.sh/oauth/token"

        self.apiv2payload = {
            "client_id": Credentials.client_id,
            "client_secret": Credentials.client_secret,
        }

        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        self.auth_template = "Bearer {}"

        self._token = ""

        self.expiration_date = datetime(1970, 1, 1)

    # self._token = token()

    def token_valid(self):
        return self.expiration_date > datetime.now()

    def update_token(self, response: requests.Response):
        pass

    def token(self):
        if not self.token_valid():
            logging.info("Sent new token request")
            response = requests.post(
                self.url, headers=self.headers, data=self.apiv2payload
            )

            if response.ok:
                logging.info("Got new token.")
                self.update_token(response)
            else:
                logging.warning(
                    "Failed to create apiv2 token:",
                    response.status_code,
                    response.json(),
                )

        return self._token

    def authorization(self):
        return self.auth_template.format(self.token())


class ApiToken(Token):
    def __init__(self):
        super().__init__()
        self.apiv2payload["grant_type"] = "client_credentials"
        self.apiv2payload["scope"] = "public"

    def update_token(self, response: requests.Response):
        self.expiration_date = datetime.now() + timedelta(
            seconds=response.json()["expires_in"]
        )
        self._token = response.json()["access_token"]
        logging.info(Credentials.refresh_token)


class ChatToken(Token):
    def __init__(self):
        super().__init__()
        self.apiv2payload["grant_type"] = "refresh_token"
        self.apiv2payload["refresh_token"] = Credentials.refresh_token

    def update_token(self, response: requests.Response):
        self.expiration_date = datetime.now() + timedelta(
            seconds=response.json()["expires_in"]
        )
        self._token = response.json()["access_token"]
        Credentials.refresh_token = response.json()["refresh_token"]
        logging.info(Credentials.refresh_token)
