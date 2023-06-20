from Utils import *
import re
from rosu_pp_py import Beatmap, Calculator
import json
import api.osuv2ApiWrapper
from Message import Message
from datetime import datetime, timedelta

### Methods working with osu!api, to be cropped and moved to Utils


class Commands:
    def __init__(self, config):
        self.osu = osuv2ApiWrapper(config)
        self.cooldown = 5
        self.request_cooldown = 1
        self.cooldowns = dict()
        self.time = datetime.strptime("20/06/2023 18:16:00", "%d/%m/%Y %H:%M:%S")

    def score_info(self, score_data):
        beatmap_attributes = self.osu.get_beatmap_attributes(
            score_data["beatmap"]["id"], generate_mods_payload(score_data["mods"])
        ).json()["attributes"]

        message = "https://osu.ppy.sh/b/" + str(score_data["beatmap"]["id"]) + " "
        message += map_name_from_response(score_data)
        message += " " + str(round(beatmap_attributes["star_rating"], 2)) + "*"
        if len(score_data["mods"]) > 0:
            message += " +"
            for mod in score_data["mods"]:
                message += mod

        message += " " + str(round(score_data["accuracy"] * 100, 2)) + "%"
        if beatmap_attributes["max_combo"] == score_data["max_combo"]:
            message += " FC"
        else:
            message += (
                " "
                + str(score_data["max_combo"])
                + "/"
                + str(beatmap_attributes["max_combo"])
                + "x"
            )
        if score_data["statistics"]["count_miss"]:
            message += " " + str(score_data["statistics"]["count_miss"]) + "xMiss"

        map_data = self.osu.get_map_data(str(score_data["beatmap"]["id"]))
        objects_passed = get_passed_objects(score_data)
        all_objects = get_objects_count(score_data)
        n100 = int(
            (score_data["statistics"]["count_100"] * all_objects) / objects_passed
        )
        n50 = int((score_data["statistics"]["count_50"] * all_objects) / objects_passed)
        acc = 100 * ((all_objects - n100 - n50) + n100 / 3 + n50 / 6) / all_objects

        calc = build_calculator(score_data)
        beatmap = Beatmap(bytes=map_data.content)

        curr_perf = calc.performance(beatmap)
        calc.set_n100(n100)
        calc.set_n50(n50)
        calc.set_n_misses(0)
        # calc.set_acc(score_data['accuracy'])
        calc.set_combo(int(beatmap_attributes["max_combo"]))
        perf = calc.performance(beatmap)

        if score_data["pp"]:
            message += " " + str(int(score_data["pp"])) + "pp"
        else:
            message += " " + str(int(curr_perf.pp + 0.5)) + "pp"
        if (
            beatmap_attributes["max_combo"] >= score_data["max_combo"] + 10
            or score_data["statistics"]["count_miss"]
        ):
            message += (
                " ("
                + str(int(perf.pp + 0.5))
                + "pp for "
                + str(round(acc, 2))
                + "% FC)"
            )
        if score_data["beatmap"]["status"] != "ranked":
            message += " if ranked"
        # message = message.replace('"', '\\"')
        message = message.replace('"', "")
        return message

    # def get_user_pair(lhs: str, rhs: str):
    #     tasks = [asyncio.ensure_future(get_user_data(u)) for u in [lhs, rhs]]
    #     users = asyncio.gather(*tasks)
    #     if users[0].ok and users[1].ok:
    #         return users

    # TODO: REWRITE IT FFS
    def get_users_from_query(self, query):
        query = re.sub("%..", " ", query)
        query = re.sub("[^a-zA-Z0-9\[\]\-_ ]", "", query)
        tokens = [x.strip() for x in query.split(" ") if x.strip()]
        query = " ".join(tokens)
        logging.info(f"'{query}'")
        logging.info(f"{tokens}")

        user_data = self.osu.get_user_data(DEFAULT_USER)
        other_data = self.osu.get_user_data(query)
        if user_data.ok and other_data.ok:
            return user_data, other_data, DEFAULT_USER, query

        for i in range(1, len(tokens)):
            user = " ".join(tokens[:i])
            other = " ".join(tokens[i:])
            user_data = self.osu.get_user_data(user)
            other_data = self.osu.get_user_data(other)
            if user_data.ok and other_data.ok:
                return user_data, other_data, user, other
        return None, None, None, None

    def prepare_ppdiff_message(self, user_data, other_data):
        userpp = user_data["statistics"]["pp"]
        otherpp = other_data["statistics"]["pp"]
        # username = username_from_response(user_data)

        if userpp > otherpp:
            message = (
                username_from_response(user_data)
                + " is "
                + str(round(userpp - otherpp, 1))
                + "pp ahead of "
                + username_from_response(other_data)
                + ". "
            )
            message += self.message_to_overtake(other_data, user_data)
        else:
            message = (
                username_from_response(user_data)
                + " is "
                + str(round(otherpp - userpp, 1))
                + "pp behind "
                + username_from_response(other_data)
                + ". "
            )
            message += self.message_to_overtake(user_data, other_data)
        return message

    def message_to_overtake(self, user_data, other_data):
        user_pp = user_data["statistics"]["pp"]
        goal_pp = other_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user_data["id"]).json()
        pp_value = pp_to_overtake(top100, user_pp, goal_pp)

        if pp_value < 0:
            return ""

        return f"{user_data['username']} needs to get a {int(pp_value + .5)}pp play to overtake {other_data['username']}"

    ###

    def ppdiff(self, request):
        if not self.cooldowns.get("ppdiff"):
            self.cooldowns["ppdiff"] = datetime.now()

        if self.cooldowns["ppdiff"] > datetime.now():
            return
        self.cooldowns["ppdiff"] = datetime.now() + timedelta(seconds=self.cooldown)

        message = ""
        query = request.message

        query = re.sub("%..", " ", query).strip()
        user_data, other_data, user, other = self.get_users_from_query(query)

        if not (user_data and other_data and (user_data.ok and other_data.ok)):
            return "Could not find such user(s) NOOOO"

        # user = username_from_response(user_data, user)
        # other = username_from_response(other_data, other)

        message = self.prepare_ppdiff_message(user_data.json(), other_data.json())
        return message

    def recent(self, request):
        if not self.cooldowns.get("recent"):
            self.cooldowns["recent"] = datetime.now()

        if self.cooldowns["recent"] > datetime.now():
            return
        self.cooldowns["recent"] = datetime.now() + timedelta(seconds=self.cooldown)

        message = ""
        user = request.message
        if not user or user.isspace():
            user = DEFAULT_USER

        user = re.sub("%..", " ", user)
        # user = user.replace('%20', ' ')
        user = " ".join([x.strip() for x in str(user).split(" ") if x.strip()])
        if len(user) == 0:
            user = DEFAULT_USER
        user_data = self.osu.get_user_data(user)
        if not user_data.ok:
            return "Invalid user"

        recent_score = self.osu.get_last_played(user_data.json()["id"])
        if not recent_score.ok or len(recent_score.json()) == 0:
            return (
                "No scores for "
                + username_from_response(user_data.json())
                + " in last 24 hours"
            )

        score_data = recent_score.json()[0]
        message = self.score_info(score_data)
        return message

    # TODO: add optional map id torecent whatif
    def whatif(self, request):
        if not self.cooldowns.get("whatif"):
            self.cooldowns["whatif"] = datetime.now()

        if self.cooldowns["whatif"] > datetime.now():
            return
        self.cooldowns["whatif"] = datetime.now() + timedelta(seconds=self.cooldown)

        try:
            query = request.message
            if not query:
                return "Usage: !whatif [pp value] [count]"

            query = re.sub("%..", " ", query)
            tokens = [x.strip() for x in query.split(" ") if x.strip()]
            if len(tokens) == 0:
                return "Usage: !whatif [pp value] [count]"
            if len(tokens) == 1:
                count = 1
            else:
                count = int(tokens[1])
            if float(tokens[0]) > 2000 or count > 100:
                return "really?"
            pps = [float(tokens[0]) for i in range(count)]
        except:
            return "Invalid arguments Tssk"

        user = DEFAULT_USER
        user_data = self.osu.get_user_data(user)
        user_data = user_data.json()
        message = username_from_response(user_data) + " needs to get a "
        full_pp = user_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user).json()
        pp_values = [score["pp"] for score in top100]
        weighted = [0.95**i * pp_values[i] for i in range(len(pp_values))]
        wsum = sum(weighted)
        bonus_pp = full_pp - wsum

        pp_values.extend(pps)
        pp_values.sort(reverse=True)
        pp_values = pp_values[:100]
        weighted = [0.95**i * pp_values[i] for i in range(len(pp_values))]
        wsum = sum(weighted)
        new_pp = wsum + bonus_pp

        message = "Prayge If " + user_data["username"] + " gets " + str(count) + " "
        message += (
            str(tokens[0])
            + "pp score(s), he would be at "
            + str(round(new_pp, 1))
            + "pp (+"
        )
        message += str(round(new_pp - full_pp, 1)) + "pp)"
        return message
        # return "Not implemented yet DEFAULT_USERBusiness"

    def recentbest(self, request):
        if not self.cooldowns.get("recentbest"):
            self.cooldowns["recentbest"] = datetime.now()

        if self.cooldowns["recentbest"] > datetime.now():
            return
        self.cooldowns["recentbest"] = datetime.now() + timedelta(seconds=self.cooldown)

        query = request.message
        if not query or query.isspace():
            query = DEFAULT_USER

        query = re.sub("%..", " ", query)
        query = " ".join([x.strip() for x in str(query).split(" ") if x.strip()])
        if len(query) == 0:
            query = DEFAULT_USER
        user_data = self.osu.get_user_data(query)
        if not user_data.ok:
            return "Unknown user MyHonestReaction"

        user_data = user_data.json()
        username = username_from_response(user_data)
        full_pp = user_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user_data["id"]).json()
        score_data = max(top100, key=lambda score: score["created_at"])
        index = [
            i + 1
            for i in range(len(top100))
            if top100[i]["beatmap"]["id"] == score_data["beatmap"]["id"]
        ][0]

        message = "Latest top score #" + str(index) + " for " + username + ": "
        message += self.score_info(score_data)
        return message

    def todaybest(self, request):
        if not self.cooldowns.get("todaybest"):
            self.cooldowns["todaybest"] = datetime.now()

        if self.cooldowns["todaybest"] > datetime.now():
            return
        self.cooldowns["todaybest"] = datetime.now() + timedelta(seconds=self.cooldown)

        query = request.message
        if not query:
            query = DEFAULT_USER
        message = ""
        place = 1
        query = re.sub("%..", " ", query)
        tokens = [x.strip() for x in str(query).split(" ") if x.strip()]
        if tokens[-1].isnumeric() and len(tokens[-1]) < 3:
            place = int(tokens.pop())
            if place <= 0:
                place = 1
        query = " ".join(tokens)
        if len(query) == 0:
            query = DEFAULT_USER
        user_data = self.osu.get_user_data(query)
        if not user_data.ok:
            return "Who is this Concerned"
        user_data = user_data.json()
        username = username_from_response(user_data)
        full_pp = user_data["statistics"]["pp"]
        recent_plays = sorted(
            self.osu.get_today_scores(user_data["id"]).json(),
            key=lambda score: float(0 if score["pp"] is None else score["pp"]),
            reverse=True,
        )
        if len(recent_plays) == 0:
            return "No scores for " + username + " in last 24 hours Sadge"
        if len(recent_plays) < place and place != 1:
            message += "Requested place unavailable, falling back to #1. "
            place = 1
        score_data = recent_plays[place - 1]

        message += "Today's score #" + str(place) + " for " + username + ": "
        message += self.score_info(score_data)
        return message

    def ppcounter(self, request):
        return "not implenented PEEPEES"

        query = request.message
        if not query:
            return "usage: !pp [map id | recent] [mods]"
        query = " ".join([x.strip() for x in query.split(" ") if x.strip()])
        if query[0].lower() == "recent":
            query = self.osu.get_last_played(DEFAULT_USER)
            if not query.ok or len(query.json()) == 0:
                return "Could not get recent score PEEPEES"
            map_id = str(query[0]["beatmap"]["id"])
            mods = str(query[0]["beatmap"]["id"])

    def req(self, msg: Message, map_id):
        if not self.cooldowns.get("req"):
            self.cooldowns["req"] = datetime.now()

        if self.cooldowns["req"] > datetime.now():
            return
        self.cooldowns["req"] = datetime.now() + timedelta(
            seconds=self.request_cooldown
        )

        # return 'ChiconyBusiness Send map link to osu!pm'
        BEATMAP_URL = "https://osu.ppy.sh/b/"
        beatmap = self.osu.get_beatmap(map_id)
        if beatmap.ok:
            map_name = map_name_from_response(beatmap.json())
            message = f"{msg.user} | [{BEATMAP_URL}{map_id} {map_name}]"
            response = self.osu.send_pm(DEFAULT_USER, message)
            return f"{msg.user} sent request: {map_name}"
        else:
            return "Seems like beatmap does not exist, are you sure dogQ"

    def timer(self, message):
        td = datetime.now() - self.time
        hours, minutes, seconds = (
            td.seconds // 3600,
            td.seconds // 60 % 60,
            int(td.seconds % 60),
        )
        return f"Current time: {hours} hours, {minutes} minutes and {seconds} seconds"

    def update_timer(self, message):
        if message.user in ["andrefq", "chicony"]:
            self.time = datetime.now()
        return f"New time: {str(self.time)}"

    # def rpp(self, request):
    #     query = request.args.get("query")
    #     user = request.args.get("user")
    #     if not query:
    #         return "RIPBOZO"
    #     try:
    #         beatmap = query.split("/")[-1]
    #         beatmap = re.sub("[^0-9]", "", beatmap)
    #         beatmap_id = int(beatmap)
    #     except:
    #         return "failed to parse beatmap id, are you sure it's correct?"

    #     beatmap = self.osu.get_beatmap(beatmap_id)
    #     if beatmap.ok:
    #         map_name = map_name_from_response(beatmap.json())
    #         message = f"{user} | [{BEATMAP_URL}{beatmap_id} {map_name}]"
    #         response = self.osu.send_pm(DEFAULT_USER, message)
    #         return f"{user} sent request: {map_name}"
    #     else:
    #         return "Seems like beatmap does not exist, are you sure dogQ"


# regex for commands - '!command_name($| .*)'
