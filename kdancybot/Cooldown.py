from kdancybot.db.Models import Settings

from datetime import datetime, timedelta


class Cooldown:
    def __init__(self, commands, default_cooldown=4, request_cooldown=1):
        self.commands = commands
        self.default_cooldown = default_cooldown
        self.request_cooldown = request_cooldown
        self.last_use = self.__create_last_use()

    def __create_last_use(self):
        last_use = dict()
        for command in self.commands:
            last_use[command] = dict()
        last_use["request"] = dict()
        return last_use

    def cd(self, command, channel):
        settings = Settings.GetSettingsByTwitchUsername(channel)
        if command == "request":
            seconds = settings.get("request_cd", self.request_cooldown)
        else:
            seconds = settings.get("commands_cd", self.default_cooldown)

        if (self.last_use[command].get(channel)) and (self.last_use[command][channel] + timedelta(seconds=seconds) > datetime.now()):
            return False
        else:
            self.last_use[command][channel] = datetime.now()
            return True
