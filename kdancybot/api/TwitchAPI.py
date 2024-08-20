from kdancybot.Token import TwitchToken
from kdancybot.Message import Message
from kdancybot.Commands import Commands

# from kdancybot.PersonalCommands import PersonalCommands
from kdancybot.Cooldown import Cooldown
from kdancybot.Utils import parse_beatmap_link
from kdancybot.db.Models import Settings, Twitch, Messages, Aliases
from kdancybot.RoutineBuilder import start_routines

import websockets
import logging
from concurrent.futures import ThreadPoolExecutor
import asyncio
import traceback

logger = logging.getLogger(__name__)

class TwitchChatHandler:
    def __init__(self, config: dict):
        self.config = config
        self.token = TwitchToken(config)
        self.commands = None
        self.routines = None
        self.settings = Settings.GetAll()  # CURRENTLY USELESS
        self.ws = None
        self.users = set()
        # self.personal_commands = PersonalCommands(config)
        self.url = "ws://irc-ws.chat.twitch.tv:80"
        self.username = config["twitch"]["username"]
        self.ignored_users = [self.username, "nightbot", "streamelements"]
        self.join_size = 20
        self.join_timeout = 10.1  # Additional 100ms just to be sure

        self.aliases = None
        self.cd = None
        self.executor = ThreadPoolExecutor(20)

    async def initialize(self):
        self.commands = await Commands.Instance(self.config)
        self.command_templates = {
            "recent": self.commands.recent,
            "recentbest": self.commands.recentbest,
            "todaybest": self.commands.todaybest,
            "ppdiff": self.commands.ppdiff,
            "whatif": self.commands.whatif,
            "top": self.commands.top,
            "profile": self.commands.profile,
            "map": self.commands.now_playing_map,
            "np": self.commands.now_playing,
            "nppp": self.commands.now_playing_pp,
            "commands": self.commands.commands,
        }
        self.cd = Cooldown(self.command_templates.keys())

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
                response = await self.commands.req(message, map_info)
                await self.respond_to_message(message, response)
                Messages.insert(
                    channel=message.channel,
                    chatter=message.user,
                    command="request",
                    message=message.message,
                ).execute()

    async def handle_commands(self, message: Message):
        if message and message.user_command:
            command = self.aliases.get(
                message.user_command,
                message.user_command
            )
            command_func = self.command_templates.get(command)
            if command_func and self.cd.cd(command, message.channel):
                response = await command_func(message)
                await self.respond_to_message(message, response)
                Messages.insert(
                    channel=message.channel,
                    chatter=message.user,
                    command=message.user_command,
                    message=message.message,
                ).execute()

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
            else:
                self.internal_channel_status_management(message)
                logger.debug(message)
        except Exception as e:
            logger.warning(traceback.format_exc())

    async def login(self):
        token = self.token.token()
        await self.ws.send(
            "CAP REQ :twitch.tv/membership twitch.tv/tags twitch.tv/commands"
        )
        await self.ws.send("PASS oauth:{}".format(token))
        await self.ws.send("NICK {}".format(self.username))

    async def __join_channels(self, users):
        if self.ws and len(users):
            for i in range(0, len(users), self.join_size):
                current_users = users[i:i+self.join_size]
                join_message = "JOIN #" + ",#".join(current_users)
                await self.ws.send(join_message)
                logger.info("Sent JOIN for channels: {}".format(", ".join(current_users)))
                await asyncio.sleep(self.join_timeout)

    async def __part_channels(self, users):
        if self.ws and len(users):
            for i in range(0, len(users), self.join_size):
                current_users = users[i:i+self.join_size]
                part_message = "PART #" + ",#".join(current_users)
                await self.ws.send(part_message)
                logger.info("Sent PART for channels: {}".format(", ".join(current_users)))
                await asyncio.sleep(self.join_timeout)

    async def join_channels(self, users):
        asyncio.create_task(self.__join_channels(users))
    
    def internal_channel_status_management(self, message):
        if message.user == "kdancybot":
            if message.type == "JOIN":
                self.users.add(message.channel)
                logger.info("Joined channel: {}".format(message.channel))
            elif message.type == "PART":
                self.users.discard(message.channel)
                logger.info("Left channel: {}".format(message.channel))

    async def part_channels(self, users):
        asyncio.create_task(self.__part_channels(users))
    
    async def join_channels_after_login(self):
        users_settings = Settings.GetAll()
        active_users = [
            u.twitch_id
            for u in users_settings
            if u.bot_on and (u.commands_on or u.request_on)
        ]
        active_usernames = [u.username for u in Twitch.GetUsersFromIds(active_users)]
        await self.join_channels([u for u in active_usernames if u not in self.users])
        # self.users = active_usernames
        
    async def loop(self):
        await self.initialize()
        async for ws in websockets.connect(self.url, ping_interval=10):
            try:
                self.reset_data_after_exception()
                self.ws = ws
                await self.login()
                await self.join_channels_after_login()
                logger.info("Joined twitch chat!")
                await self.start_routines()
                while True:
                    received = await ws.recv()
                    message = Message(received)
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
        self.users = set()

    async def check_channels(self):
        users_settings = Settings.GetAll()
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
        # self.users = active_usernames

    async def update_settings(self):
        logger.info("Updating settings")
        self.settings = Settings.GetAll()

    async def update_aliases(self):
        logger.info("Updating aliases")
        self.aliases = Aliases.GetAll()

    # Twitch seems to disconnect user if they don't send a message
    # for 11 minutes, this function exists to (in hacky way) fix that problem
    # by faking activity via sending an empty message
    async def _send_message_untimeout(self):
        if self.ws:
            message = "PRIVMSG #{} :{}".format(self.username, "")
            await self.ws.send(message)
        
    async def start_routines(self):
        if not self.routines:
            self.routines = await start_routines(
                {"func": self.check_channels, "delay": 60},
                {"func": self.update_settings, "delay": 150},
                {"func": self._send_message_untimeout, "delay": 300},
                {"func": self.update_aliases, "delay": 3600},
            )
