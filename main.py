import websockets
import asyncio
import configparser
from kdancybot.api.TwitchAPI import TwitchChatHandler
import logging

configfile = "config.ini"

logging.basicConfig(
    filename='osubot.log',
    level=logging.INFO,
    format="%(asctime)s - %(name)-25s - %(levelname)s - %(message)s",
)

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(configfile)
    twitch = TwitchChatHandler(config)
    asyncio.run(
        twitch.loop(),
        # debug=True
    )
