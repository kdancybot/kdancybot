#!bin/python

import websockets
import asyncio
import configparser
from kdancybot.api.TwitchAPI import TwitchChatHandler
import logging
import argparse

logging.basicConfig(
    filename="logs/osubot.log",
    level=logging.INFO,
    format="%(asctime)s - %(name)-25s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", "--configfile", default="config.ini")
    return parser


def read_config():
    parser = create_parser()
    args = parser.parse_args()
    config = configparser.ConfigParser()
    successfully_read_files = config.read(args.config)
    if len(successfully_read_files) == 0:
        logger.error(f"Invalid config file(s): {args.config}")
        exit("No valid config files provided")
    return config


def run():
    logger.info("Started running!")
    config = read_config()
    twitch = TwitchChatHandler(config)
    asyncio.run(
        twitch.loop(),
        # debug=True
    )


if __name__ == "__main__":
    run()
