from kdancybot.Token import TwitchToken
from kdancybot.Message import Message
from kdancybot.Commands import Commands

# from kdancybot.PersonalCommands import PersonalCommands
from kdancybot.Timer import Timer
from kdancybot.Cooldown import Cooldown
from kdancybot.Utils import parse_beatmap_link
from kdancybot.db.Models import Settings, Osu, Twitch
from kdancybot.RoutineBuilder import start_routines

import websockets
import re
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import traceback
import threading
import time

logger = logging.getLogger(__name__)


class TwitchChatHandler:
    def __init__(self, config: dict):
        self.config = config
        self.token = TwitchToken(config)
        self.commands = Commands(config)
        self.routines = None
        self.settings = Settings.GetAllSettings()  # CURRENTLY USELESS
        self.ws = None
        self.users = list()
        # self.personal_commands = PersonalCommands(config)
        self.url = "ws://irc-ws.chat.twitch.tv:80"
        self.username = config["twitch"]["username"]
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
            "top": self.commands.top,
            "profile": self.commands.profile,
            "np": self.commands.now_playing,
            "nppp": self.commands.now_playing_pp,
            "к": self.commands.recent,
            "ки": self.commands.recentbest,
            "еи": self.commands.todaybest,
            "црфеша": self.commands.whatif,
            "ещз": self.commands.top,
            "тз": self.commands.now_playing,
        }

        self.cd = Cooldown(self.command_templates.keys())
        self.executor = ThreadPoolExecutor(20)

    async def respond_to_message(self, message, response):
        if self.ws and response:
            await self.ws.send(
                "@reply-parent-msg-id={} PRIVMSG #{} :{}".format(
                    message.tags.get("id", 0), message.channel, response
                )
            )

    async def handle_requests(self, message):
        if message.user.lower() not in self.ignored_users:
            map_info = parse_beatmap_link(message.message)
            if map_info and self.cd.cd("request", message.channel):
                response = await asyncio.get_event_loop().run_in_executor(
                    self.executor, self.commands.req, message, map_info
                )
                await self.respond_to_message(message, response)

    async def handle_commands(self, message: Message):
        if message and message.user_command:
            # personal_command_func = self.personal_commands[message.channel].get(
            #     message.user_command
            # )
            command_func = self.command_templates.get(message.user_command)
            # if personal_command_func:
            #     ret = await asyncio.get_event_loop().run_in_executor(
            #         self.executor, personal_command_func, message
            #     )
            #     await self.respond_to_message(message, ret)
            # el
            if command_func and self.cd.cd(message.user_command, message.channel):
                ret = await asyncio.get_event_loop().run_in_executor(
                    self.executor, command_func, message
                )
                await self.respond_to_message(message, ret)

    async def handle_privmsg(self, message):
        # await asyncio.gather(
        #     self.handle_requests(ws, message), self.handle_commands(ws, message)
        # )
        settings = Settings.GetSettingsByTwitchUsername(message.channel)
        if settings["request_on"]:
            await self.handle_requests(message)
        if settings["commands_on"]:
            await self.handle_commands(message)

    async def handle_message(self, message):
        try:
            if message.type == "PRIVMSG":
                await self.handle_privmsg(message)
        except Exception as e:
            logger.warning(traceback.format_exc())

    async def login(self):
        token = self.token.token()
        # await asyncio.get_event_loop().run_in_executor(
        #     self.executor, self.token.token
        # )
        await self.ws.send(
            "CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands"
        )
        await self.ws.send("PASS oauth:{}".format(token))
        await self.ws.send("NICK {}".format(self.username))

    async def join_channels(self, users):
        if self.ws and len(users):
            join_message = "JOIN #" + ",#".join(users)
            await self.ws.send(join_message)
            logger.info("Joined channels: {}".format(", ".join(users)))

    async def part_channels(self, users):
        if self.ws and len(users):
            part_message = "PART #" + ",#".join(users)
            await self.ws.send(part_message)
            logger.info("Left channels: {}".format(", ".join(users)))

    async def loop(self):
        async for ws in websockets.connect(self.url):
            try:
                self.ws = ws
                await self.login()
                await self.check_channels()
                logger.info("Joined twitch chat!")
                await self.start_routines()
                while True:
                    message = Message(await ws.recv())
                    logger.debug(message)
                    asyncio.create_task(self.handle_message(message))
            except Exception as e:
                self.reset_data_after_exception()
                if isinstance(e, websockets.exceptions.ConnectionClosed):
                    logger.warning(
                        "Twitch WS connection closed%s",
                        " abnormally"
                        if isinstance(e, websockets.exceptions.ConnectionClosedError)
                        else "",
                    )
                else:
                    await asyncio.sleep(10)
                logger.warning(traceback.format_exc())
                continue

    def reset_data_after_exception(self):
        self.ws = None
        self.users = list()

    async def check_channels(self):
        users_settings = Settings.GetAllSettings()
        active_users = [
            u.twitch_id
            for u in users_settings
            if u.bot_on and (u.commands_on or u.request_on)
        ]
        inactive_users = [
            u.twitch_id for u in users_settings if u.twitch_id not in active_users
        ]
        active_usernames = [u.username for u in Twitch.GetUsersFromIds(active_users)]
        await self.join_channels([u for u in active_usernames if u not in self.users])
        await self.part_channels(
            [
                u.username
                for u in Twitch.GetUsersFromIds(inactive_users)
                if u.username in self.users
            ]
        )
        self.users = active_usernames

    async def update_settings(self):    
        logger.info("Updating settings")
        self.settings = Settings.GetAllSettings()

    async def start_routines(self):
        if not self.routines:
            self.routines = await start_routines(
                {"func": self.check_channels, "delay": 60},
                {"func": self.update_settings, "delay": 200},
            )
