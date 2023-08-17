def WelterSkin(message: any):
    return "https://drive.google.com/file/d/1j5hOWahZrWK4m6Vwr_pH0EKGc5XrHaT-/view"


class PersonalCommands:
    def __init__(self, config):
        self.config = config
        self.users = config["users"]
        self.commands = dict()
        for user in self.users:
            self.commands[user] = dict()
        self.commands["welterss"]["skin"] = WelterSkin

    def __getitem__(self, value: str):
        return self.commands[value]
