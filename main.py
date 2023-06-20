import websockets
import asyncio
import configparser
from twitchapi import TwitchChatHandler

configfile = "config.ini"

if __name__ == "__main__":
    config = configparser.ConfigParser()
    config.read(configfile)
    twitch = TwitchChatHandler(config)
    asyncio.run(twitch.loop())
