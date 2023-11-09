import requests
import logging
import configparser

logger = logging.getLogger(__name__)

config = configparser.SafeConfigParser()
config.read("config.ini")

class NPClient:
    def any_request(url: str, http_method: str, **kwargs):
        data = kwargs.get("data")
        headers = kwargs.get("headers", {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            }
        )
        logger.debug(
            f"Requesting with {http_method} method from {url} with kwargs: {kwargs}"
        )
        r = requests.request(http_method, url, headers=headers, data=data)  # .json()
        logger.debug(f"Got {r.status_code} code")
        return r

    def api_request(endpoint: str, http_method: str, **kwargs):
        return NPClient.any_request(f"{Template.base}{endpoint}", http_method, **kwargs)

    def get_request(endpoint: str, **kwargs):
        return NPClient.api_request(endpoint, "get", **kwargs)

    def post_request(endpoint: str, **kwargs):
        return NPClient.api_request(endpoint, "post", **kwargs)

    # Custom requests

    def send_command(client, command):
        endpoint = f"send_command?client={client}&command={command}"
        response = NPClient.get_request(endpoint)
        return response

    def get_np(client):
        return NPClient.send_command(client, "np")


class Template:
    base = f"{config.get('np', 'protocol')}://{config.get('np', 'address')}:{config.get('np', 'port')}/"
