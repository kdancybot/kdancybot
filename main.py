#!bin/python

import websockets
import asyncio
import configparser
from kdancybot.api.TwitchAPI import TwitchChatHandler
import logging

configfile = "config.ini"

logging.basicConfig(
    filename="osubot.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)-25s - %(levelname)s - %(message)s",
)


def run():
    config = configparser.ConfigParser()
    config.read(configfile)
    twitch = TwitchChatHandler(config)
    asyncio.run(
        twitch.loop(),
        # debug=True
    )


if __name__ == "__main__":
    run()
