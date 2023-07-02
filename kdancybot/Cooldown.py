from datetime import datetime, timedelta


class Cooldown:
    def __init__(self, commands, channels, default_cooldown=4, request_cooldown=1):
        self.commands = commands
        self.channels = channels
        self.default_cooldown = default_cooldown
        self.request_cooldown = request_cooldown
        self.cooldown = self.__create_cooldown()
        self.next_use = self.__create_next_use()

    def __create_cooldown(self):
        cooldown = dict()
        for command in self.commands:
            cooldown[command] = dict()
            for channel in self.channels:
                cooldown[command][channel] = self.default_cooldown

        cooldown["request"] = dict()
        for channel in self.channels:
            cooldown["request"][channel] = self.request_cooldown
        return cooldown

    def __create_next_use(self):
        next_use = dict()
        for command in self.commands:
            next_use[command] = dict()
        next_use["request"] = dict()
        return next_use

    def cd(self, command, channel):
        if not self.next_use[command].get(channel):
            self.next_use[command][channel] = datetime.now()
        # logging.debug(channel, method)
        if self.next_use[command][channel] > datetime.now():
            return False
        self.next_use[command][channel] = datetime.now() + timedelta(
            seconds=self.cooldown.get(command, {}).get(channel, 5)
        )
        return True
