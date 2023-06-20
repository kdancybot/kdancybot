import requests
import logging
from Credentials import Credentials
from datetime import datetime, timedelta


class Token:
    def __init__(self, config):
        self.url = "https://osu.ppy.sh/oauth/token"

        self.config = config

        self.data = {
            "client_id": config["osu"]["client_id"],
            "client_secret": config["osu"]["client_secret"],
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

    def update_config(self):
        with open("config.ini", "w") as configfile:
            self.config.write(configfile)

    def token(self):
        if not self.token_valid():
            logging.info("Sent new token request")
            response = requests.post(self.url, headers=self.headers, data=self.data)

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
    def __init__(self, config):
        super().__init__(config)
        self.data["grant_type"] = "client_credentials"
        self.data["scope"] = "public"

    def update_token(self, response: requests.Response):
        self.expiration_date = datetime.now() + timedelta(
            seconds=response.json()["expires_in"]
        )
        self._token = response.json()["access_token"]


class ChatToken(Token):
    def __init__(self, config):
        super().__init__(config)
        self.data["grant_type"] = "refresh_token"
        self.data["refresh_token"] = self.config["osu"]["refresh_token"]

    def update_token(self, response: requests.Response):
        self.expiration_date = datetime.now() + timedelta(
            seconds=response.json()["expires_in"]
        )
        self._token = response.json()["access_token"]
        self.data["refresh_token"] = response.json()["refresh_token"]
        self.config["osu"]["refresh_token"] = self.data["refresh_token"]
        logging.debug(self.config["osu"]["refresh_token"])

        # Saving token like this for now
        f = open("refresh_token.txt", "w")
        f.write(self.config["osu"]["refresh_token"])
        f.close()

        self.update_config()


class TwitchToken(Token):
    def __init__(self, config):
        super().__init__(config)
        self.url = "https://id.twitch.tv/oauth2/token"
        self.data["client_id"] = config["twitch"]["client_id"]
        self.data["client_secret"] = config["twitch"]["client_secret"]
        self.data["grant_type"] = "refresh_token"
        self.data["refresh_token"] = config["twitch"]["refresh_token"]

    def update_token(self, response: requests.Response):
        self.expiration_date = datetime.now() + timedelta(
            seconds=response.json().get("expires_in", 3600)
        )
        self._token = response.json()["access_token"]
        self.data["refresh_token"] = response.json()["refresh_token"]
        self.config["twitch"]["refresh_token"] = self.data["refresh_token"]
        logging.debug(self.config["twitch"]["refresh_token"])

        # Saving token like this for now
        f = open("refresh_token_twitch.txt", "w")
        f.write(self.config["twitch"]["refresh_token"])
        f.close()

        self.update_config()
