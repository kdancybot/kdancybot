import requests
import logging

from Token import ApiToken, ChatToken


class osuv2ApiWrapper:
    def __init__(self, config):
        super().__init__()
        self.api_token = ApiToken(config)
        self.chat_token = ChatToken(config)
        self.request_headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        }

    def api_headers(self):
        self.request_headers["Authorization"] = self.api_token.authorization()
        return self.request_headers

    def chat_headers(self):
        self.request_headers["Authorization"] = self.chat_token.authorization()
        return self.request_headers

    def any_request(self, url: str, http_method: str, **kwargs):
        headers = kwargs.get("headers")
        data = kwargs.get("data")
        logging.info(
            f"Requesting with {http_method} method from {url} with kwargs: {kwargs}"
        )
        r = requests.request(http_method, url, headers=headers, data=data)  # .json()
        logging.info(f"Got {r.status_code} code")
        return r

    def api_request(self, endpoint: str, http_method: str, **kwargs):
        return self.any_request(f"{Template.base}{endpoint}", http_method, **kwargs)

    def get_request(self, endpoint: str, **kwargs):
        return self.api_request(endpoint, "get", **kwargs)

    def post_request(self, endpoint: str, **kwargs):
        return self.api_request(endpoint, "post", **kwargs)

    # Custom requests

    def get_user_data(self, user):
        endpoint = f"{Template.users}{str(user)}/osu"
        response = self.get_request(endpoint, headers=self.api_headers())
        # breakpoint()
        return response

    def get_map_data(self, id):
        url = f"https://osu.ppy.sh/osu/{id}"
        response = self.any_request(url, "get", headers={})
        return response

    def get_last_played(self, user):
        endpoint = f"{Template.users}{str(user)}/scores/recent?limit=1&include_fails=1"
        response = self.get_request(endpoint, headers=self.api_headers())
        return response

    # Currently unused. TODO: Remove method or add functionality to the bot
    def get_last_submitted(self, user):
        endpoint = f"{Template.users}{str(user)}/scores/recent?limit=1"
        response = self.get_request(endpoint, headers=self.api_headers())
        return response

    def get_today_scores(self, user):
        endpoint = (
            f"{Template.users}{str(user)}/scores/recent?limit=1000&include_fails=0"
        )
        response = self.get_request(endpoint, headers=self.api_headers())
        return response

    def get_top_100(self, user):
        endpoint = f"{Template.users}{str(user)}/scores/best?limit=100"
        response = self.get_request(endpoint, headers=self.api_headers())
        return response

    def get_beatmap_attributes(self, beatmap_id, mods=""):
        endpoint = f"{Template.beatmaps}{beatmap_id}/attributes"
        # data = generate_mods_payload(mods)
        data = mods
        response = self.post_request(endpoint, headers=self.api_headers(), data=data)
        return response

    def get_beatmap(self, beatmap_id):
        endpoint = f"{Template.beatmaps}{beatmap_id}"
        response = self.get_request(endpoint, headers=self.api_headers())
        return response

    # Chat methods

    def send_pm(self, target_id, message="default message", is_action=False):
        endpoint = f"{Template.chat}new"
        data = {"target_id": target_id, "message": message, "is_action": is_action}
        response = self.post_request(endpoint, headers=self.chat_headers(), data=data)
        return response

    # TODO: Reimplement osu! IRC chat methods below
    def send_message_to_chat(self, channel, message, is_action="false"):
        endpoint = f"{Template.chat}channels/{str(channel)}/messages"
        data = {"message": message, "is_action": is_action}
        response = self.post_request(endpoint, headers=self.chat_headers(), data=data)
        if response.ok:
            chat = response.json()["channel"]
        return response


class Template:
    base = "https://osu.ppy.sh/api/v2/"
    users = "users/"
    beatmaps = "beatmaps/"
    chat = "chat/"
