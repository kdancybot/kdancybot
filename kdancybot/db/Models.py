import configparser
from playhouse.shortcuts import ReconnectMixin
from peewee import (
    Model,
    MySQLDatabase,
    CharField,
    DateTimeField,
    IntegerField,
    AutoField,
    BooleanField,
    ForeignKeyField,
)


class ReconnectMySQLDatabase(ReconnectMixin, MySQLDatabase):
    pass


config = configparser.ConfigParser()
config.read("config.ini")

# Read database credentials from the configuration file
database_name = config.get("db", "database")
user = config.get("db", "user")
password = config.get("db", "password")
host = config.get("db", "host")

# Replace these with your MySQL connection details
db = ReconnectMySQLDatabase(
    database_name,
    user=user,
    password=password,
    host=host,
)


class Messages(Model):
    id = IntegerField(primary_key=True)
    channel = CharField(max_length=25, null=True)
    chatter = CharField(max_length=25, null=True)
    command = CharField(max_length=15, null=True)
    message = CharField(max_length=500, null=True)

    class Meta:
        database = db
        table_name = "messages"


class Twitch(Model):
    id = IntegerField(primary_key=True)
    refresh_token = CharField(max_length=50, null=True)
    access_token = CharField(max_length=1024, null=True)
    revoke_time = DateTimeField(null=True)
    username = CharField(max_length=25)
    avatar_url = CharField(max_length=256, null=True)

    class Meta:
        database = db
        table_name = "twitch"

    def GetAllUsernames():
        return [u.username for u in Twitch.select()]

    def GetUsersDict():
        return {
            u["twitch_username"].lower(): u["osu_id"]
            for u in Twitch.select(
                Twitch.username.alias("twitch_username"),
                Osu.id.alias("osu_id")
            )
            .join(Settings)
            .join(Osu)
            .dicts()
        }

    def GetUsersFromIds(users_ids):
        return Twitch.select().where(Twitch.id << users_ids)


class Osu(Model):
    id = IntegerField(primary_key=True)
    refresh_token = CharField(max_length=772, null=True)
    access_token = CharField(max_length=1024, null=True)
    revoke_time = DateTimeField(null=True)
    username = CharField(max_length=16)
    avatar_url = CharField(max_length=256, null=True)

    class Meta:
        database = db
        table_name = "osu"

    def GetUserByTwitchUsername(username):
        user = (
            Osu.select()
            .join(Settings)
            .join(Twitch)
            .where(Twitch.username == username)
            .get()
        )
        return user


class Settings(Model):
    id = AutoField(primary_key=True)
    osu_id = ForeignKeyField(Osu, backref="settings")
    twitch_id = ForeignKeyField(Twitch, backref="settings")
    bot_on = BooleanField(default=False)
    request_on = BooleanField(default=True)
    commands_on = BooleanField(default=True)
    request_cd = IntegerField(default=1)
    commands_cd = IntegerField(default=5)

    class Meta:
        database = db
        table_name = "settings"

    def GetSettingsByTwitchUsername(username):
        user = (
            Settings.select()
            .join(Twitch)
            .where(Twitch.username == username)
            .dicts()
            .get()
        )
        return user

    def GetSettingsByOsuUsername(username):
        user = (
            Settings
            .select()
            .join(Osu)
            .where(Osu.username == username)
            .dicts()
            .get()
        )
        return user

    def GetAll():
        return Settings.select()


class Aliases(Model):
    alias = CharField(max_length=25, primary_key=True)
    command = CharField(max_length=25)

    class Meta:
        database = db
        table_name = "aliases"

    def GetAll():
        return {alias.alias: alias.command for alias in Aliases.select()}


# Create the tables
db.create_tables([Twitch, Osu, Settings, Messages, Aliases])
