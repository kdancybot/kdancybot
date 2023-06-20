from Token import TwitchToken
from Message import Message
import websockets
import re
import logging
from Commands import Commands


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
        self.token = TwitchToken(config)
        self.commands = Commands(config)
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
            "time": self.commands.timer,
            "update_timer": self.commands.update_timer,
        }

    async def handle_requests(self, ws, message):
        if message.user.lower() not in self.ignored_users:
            map_id = parse_beatmap_link(message.message)
            if map_id:
                ret = self.commands.req(message, map_id)
                if ret:
                    await ws.send("PRIVMSG #{} :{}".format(message.channel, ret))

    async def handle_commands(self, ws, message):
        if message.user.lower() not in self.ignored_users:
            map_id = parse_beatmap_link(message.message)
            if map_id:
                ret = self.commands.req(message, map_id)
                if ret:
                    await ws.send("PRIVMSG #{} :{}".format(message.channel, ret))
        # logging.warning(message.message[0])
        if message.message[0] == "!":
            command = message.message.split()[0][1:]
            command_func = self.command_templates.get(command)
            if command_func:
                message.message = " ".join(
                    [
                        x.strip().lower()
                        for x in message.message.split(" ")[1:]
                        if x.strip()
                    ]
                )
                ret = command_func(message)
                if ret:
                    await ws.send("PRIVMSG #{} :{}".format(message.channel, ret))

    async def handle_privmsg(self, ws, message):
        # await asyncio.gather(
        #     self.handle_requests(ws, message), self.handle_commands(ws, message)
        # )
        await self.handle_commands(ws, message)

    async def handle_message(self, ws, message):
        try:
            if message.type == "PRIVMSG":
                await self.handle_privmsg(ws, message)
        except Exception:
            pass

    async def login(self, ws):
        await ws.send("CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands")
        await ws.send("PASS oauth:{}".format(self.token.token()))
        await ws.send("NICK {}".format(self.username))

    async def join_channels(self, ws):
        await ws.send("JOIN #chicony")

    async def loop(self):
        async with websockets.connect(self.url) as ws:
            await self.login(ws)
            await self.join_channels(ws)
            logging.warning("Joined twitch chat!")
            while True:
                try:
                    msg = await ws.recv()
                    message = Message(msg)
                    logging.warning(message.message)
                    await self.handle_message(ws, message)
                except websockets.exceptions.ConnectionClosedError:
                    pass
