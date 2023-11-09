from kdancybot.db.Models import Twitch


def WelterSkin(message: any):
    return "https://drive.google.com/file/d/1j5hOWahZrWK4m6Vwr_pH0EKGc5XrHaT-/view"


# class PersonalCommands:
#     def __init__(self, config):
#         self.config = config
#         self.users = Twitch.GetAllUsernames()
#         self.commands = dict()
#         for user in self.users:
#             self.commands[user] = dict()
#         if self.commands.get("Andrefq"):
#             self.commands.get("Andrefq")["skin"] = WelterSkin

#     def __getitem__(self, value: str):
#         return self.commands.get(value)
