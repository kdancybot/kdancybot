import websockets
import asyncio
import configparser
from kdancybot.api.TwitchAPI import TwitchChatHandler
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

# Здравствуйте мистер Илья Вопроссофф. Я обращаюсь к вам с официальным предложением подключения бота для осу.
