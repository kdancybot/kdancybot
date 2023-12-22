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
        try:
            r = requests.request(
                http_method,
                url,
                headers=headers,
                data=data,
                timeout=3
            )
            logger.debug(f"Got {r.status_code} code")
        except requests.ConnectTimeout:
            return {"error": "Response timeout"}
        return r

    def api_request(endpoint: str, http_method: str, **kwargs):
        return NPClient.any_request(
            f"{Template.base}{endpoint}",
            http_method,
            **kwargs
        )

    def get_request(endpoint: str, **kwargs):
        return NPClient.api_request(endpoint, "get", **kwargs)

    def post_request(endpoint: str, **kwargs):
        return NPClient.api_request(endpoint, "post", **kwargs)

    # Custom requests

    def send_command(client, command):
        endpoint = f"send_command?client={client}&command={command}"
        response = NPClient.get_request(endpoint)
        return response

    # Encoding type is set explicitly to make sure
    # StreamCompanion's data decodes fine
    def get_np(client):
        request_limit = 3
        for _ in range(request_limit):
            data = NPClient.send_command(client, "np")
            data.encoding = 'utf-8-sig'

            # Really nasty fix, basically we get an error field in response json
            # only when both of np data providers failed or osu! is not loaded yet.
            # Latter error return string in error field, and former returns
            # array of two elements. If one of them contains "Client.Timeout",
            # we know that data hasn't been sent because of np data provider's
            # timeout and request can be re-sent.

            error = data.json().get("error", [])
            logger.info(error)
            if (any(
                [message for message in error if "Client.Timeout" in message]
            )): 
                continue
            # Nasty fix ends here

            return data


class Template:
    base = f"{config.get('np', 'protocol')}://{config.get('np', 'address')}:{config.get('np', 'port')}/"
