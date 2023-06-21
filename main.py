import websockets
import asyncio
import configparser
from twitchapi import TwitchChatHandler
import logging

configfile = "config.ini"

logger = logging.getLogger("websockets")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logging.basicConfig(filename="osubot.log")

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(configfile)
    twitch = TwitchChatHandler(config)
    asyncio.run(
        twitch.loop(),
        # debug=True
    )
