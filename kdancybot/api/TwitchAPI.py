from kdancybot.Token import TwitchToken
from kdancybot.Message import Message
from kdancybot.Commands import Commands
from kdancybot.Timer import Timer

import websockets
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import traceback


def parse_beatmap_link(message):
    patterns = {
        "official": r"osu.ppy.sh\/beatmapsets\/[0-9]+\#(osu|taiko|fruits|mania)\/(?P<map_id>[0-9]+)",
        "official_alt": r"osu.ppy.sh\/beatmaps\/(?P<map_id>[0-9]+)",
        "old_single": r"(osu|old).ppy.sh\/b\/(?P<map_id>[0-9]+)",
    }

    for link_type, pattern in patterns.items():
        result = re.search(pattern, message)

        # If there is no match, search for old beatmap link
        if result is None:
            continue
        else:
            return result["map_id"]

    return None


class TwitchChatHandler:
    def __init__(self, config: dict):
        self.config = config
        self.token = TwitchToken(config)
        self.commands = Commands(config)
        self.timer = Timer(4, 26, 0)
        self.url = "ws://irc-ws.chat.twitch.tv:80"
        self.username = "kdancybot"
        self.ignored_users = [self.username, "nightbot", "streamelements"]
        self.command_templates = {
            "r": self.commands.recent,
            "recent": self.commands.recent,
            "rb": self.commands.recentbest,
            "recentbest": self.commands.recentbest,
            "tb": self.commands.todaybest,
            "todaybest": self.commands.todaybest,
            "ppdiff": self.commands.ppdiff,
            "whatif": self.commands.whatif,
            "time": self.timer.time,
            "pause": self.timer.pause,
            "resume": self.timer.resume,
        }
        self.executor = ThreadPoolExecutor(10)

    async def handle_requests(self, ws, message):
        if message.user.lower() not in self.ignored_users:
            map_id = parse_beatmap_link(message.message)
            if map_id:
                ret = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.commands.req, message, map_id
                )
                if ret:
                    await ws.send("PRIVMSG #{} :{}".format(message.channel, ret))

    async def handle_commands(self, ws, message: Message):
        # logging.warning(message.message[0])
        if message and message.message and message.message[0] == "!":
            # command = message.message.split()[0][1:]
            command_func = self.command_templates.get(message.user_command)
            if command_func:
                # message.message = " ".join(
                #     [
                #         x.strip().lower()
                #         for x in message.message.split(" ")[1:]
                #         if x.strip()
                #     ]
                # )
                ret = await asyncio.get_event_loop().run_in_executor(
                    self.executor, command_func, message
                )
                if ret:
                    await ws.send("PRIVMSG #{} :{}".format(message.channel, ret))

    async def handle_privmsg(self, ws, message):
        # await asyncio.gather(
        #     self.handle_requests(ws, message), self.handle_commands(ws, message)
        # )
        if not self.config["ignore_requests"].get(message.channel):
            await self.handle_requests(ws, message)
        if not self.config["ignore_commands"].get(message.channel):
            await self.handle_commands(ws, message)

    async def handle_message(self, ws, message):
        try:
            if message.type == "PRIVMSG":
                await self.handle_privmsg(ws, message)
        except Exception as e:
            logging.warning(traceback.print_exc())
            # logging.warning(e)

    async def login(self, ws):
        token = await asyncio.get_event_loop().run_in_executor(
            self.executor, self.token.token
        )
        await ws.send("CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands")
        await ws.send("PASS oauth:{}".format(token))
        await ws.send("NICK {}".format(self.username))

    async def join_channels(self, ws):
        join_message = "JOIN #" + ",#".join(
            [channel for channel in self.config["users"].keys()]
        )
        await ws.send(join_message)

    async def loop(self):
        async for ws in websockets.connect(self.url):
            try:
                await self.login(ws)
                await self.join_channels(ws)
                logging.warning("Joined twitch chat!")
                while True:
                    msg = await ws.recv()
                    message = Message(msg)
                    await self.handle_message(ws, message)
            except websockets.exceptions.ConnectionClosed:
                continue
