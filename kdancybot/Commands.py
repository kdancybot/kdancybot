from kdancybot.Utils import *
import kdancybot.api.osuAPI
from kdancybot.Message import Message
from kdancybot.Parsing import Parsing

import re
from rosu_pp_py import Beatmap, Calculator
import json
from datetime import datetime, timedelta
import logging


### Methods working with osu!api, to be cropped and moved to Utils


class Commands:
    def __init__(self, config):
        self.osu = kdancybot.api.osuAPI.osuAPIv2(config)
        self.config = config
        self.users = config["users"]
        # self.cooldowns = dict()
        # for user in self.users.keys():
        #     self.cooldowns[user] = dict()

    def score_info(self, score_data, remove_https=False):
        beatmap_attributes = self.osu.get_beatmap_attributes(
            score_data["beatmap"]["id"], generate_mods_payload(score_data["mods"])
        ).json()["attributes"]

        message = str()
        if not remove_https:
            message = "https://"
        message += "osu.ppy.sh/b/" + str(score_data["beatmap"]["id"]) + " "
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
        n300 = int(
            (score_data["statistics"]["count_300"] * all_objects) / objects_passed
        )
        n100 = int(
            (score_data["statistics"]["count_100"] * all_objects) / objects_passed
        )
        n50 = int((score_data["statistics"]["count_50"] * all_objects) / objects_passed)
        acc = 100 * ((all_objects - n100 - n50) + n100 / 3 + n50 / 6) / all_objects

        calc = build_calculator(score_data)
        beatmap = Beatmap(bytes=map_data.content)

        curr_perf = calc.performance(beatmap)
        calc.set_passed_objects(all_objects)
        calc.set_n300(n300)
        calc.set_n100(n100)
        calc.set_n50(n50)
        calc.set_n_misses(0)
        # calc.set_acc(score_data['accuracy'])
        calc.set_combo(int(beatmap_attributes["max_combo"]))
        perf = calc.performance(beatmap)

        if score_data["pp"]:
            message += " " + str(int(score_data["pp"] + 0.5)) + "pp"
        else:
            message += " " + str(int(curr_perf.pp + 0.5)) + "pp"
        if (
            beatmap_attributes["max_combo"] >= score_data["max_combo"] + 10
            or score_data["statistics"]["count_miss"]
        ):
            message += " (" + str(int(perf.pp + 0.5)) + "pp for "
            if acc == 100:
                message += "SS)"
            else:
                message += str(round(acc, 2)) + "% FC)"

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
    def get_users_from_query(self, query, request):
        query = [re.sub("[^a-zA-Z0-9\[\]\-_ ]", "", word).strip() for word in query]
        tokens = [x for x in query if x]
        query = " ".join(tokens)
        logging.info(f"'{query}'")
        logging.info(f"{tokens}")

        user_data = self.osu.get_user_data(self.users.get(request.channel))
        other_data = self.osu.get_user_data(query)
        if user_data.ok and other_data.ok:
            return user_data, other_data, self.users.get(request.channel), query

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
    # def cooldown(self, channel, method, cd):
    #     if not self.cooldowns[channel].get(method):
    #         self.cooldowns[channel][method] = datetime.now()
    #     logging.debug(channel, method)
    #     if self.cooldowns[channel][method] > datetime.now():
    #         return False
    #     self.cooldowns[channel][method] = datetime.now() + timedelta(seconds=cd)
    #     return True

    def ppdiff(self, request):
        message = ""
        query = request.arguments

        user_data, other_data, user, other = self.get_users_from_query(query, request)

        if not (user_data and other_data and (user_data.ok and other_data.ok)):
            return "Could not find such user(s) NOOOO"

        message = self.prepare_ppdiff_message(user_data.json(), other_data.json())
        return message

    def recent(self, request):
        args = Parsing.Top(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1

        message = ""

        # user = user.replace('%20', ' ')
        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Who is this Concerned"

        recent_score = self.osu.get_last_played(user_data.json()["id"])
        if not recent_score.ok or len(recent_score.json()) == 0:
            return (
                "No scores for "
                + username_from_response(user_data.json())
                + " in last 24 hours"
            )
        elif len(recent_score.json()) <= args["index"]:
            message += "Requested place unavailable, falling back to most recent. "
            args["index"] = 1

        score_data = recent_score.json()[args["index"] - 1]
        message += self.score_info(
            score_data,
            remove_https=request.channel in self.config["ignore_requests"].keys(),
        )
        return message

    def top(self, request):
        args = Parsing.Top(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1

        message = ""
        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Who is this Concerned"
        user_data = user_data.json()
        username = username_from_response(user_data)
        full_pp = user_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user_data["id"]).json()
        if len(top100) == 0:
            return "No scores for " + username + " in last 24 hours Sadge"
        if len(top100) < args["index"] and args["index"] != 1:
            message += "Requested place unavailable, falling back to #1. "
            args["index"] = 1
        score_data = top100[args["index"] - 1]

        message += ordinal(args["index"]) + " top score for " + username + ": "
        message += self.score_info(
            score_data,
            remove_https=(request.channel in self.config["ignore_requests"].keys()),
        )
        return message

    # TODO: add optional map id to recent whatif
    def whatif(self, request):
        try:
            tokens = request.arguments
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

        user = self.users.get(request.channel)
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
        # return "Not implemented yet self.users.get(request.channel)Business"

    def recentbest(self, request):
        args = Parsing.Top(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1

        message = ""
        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Unknown user MyHonestReaction"

        user_data = user_data.json()
        username = username_from_response(user_data)
        full_pp = user_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user_data["id"]).json()

        if len(top100) == 0:
            return "Bro's profile is wiped Sadge"
        elif len(top100) < args["index"] and args["index"] != 1:
            # message += "Requested place unavailable, falling back to most recent top 100 score. "
            args["index"] = 1

        ordered = sorted(
            top100,
            key=lambda score: score["created_at"],
            reverse=True,
        )
        score_data = ordered[args["index"] - 1]
        index = next(
            i + 1
            for i in range(len(top100))
            if top100[i]["beatmap"]["id"] == score_data["beatmap"]["id"]
        )

        message += "Latest top score #" + str(index) + " for " + username + ": "
        message += self.score_info(
            score_data,
            remove_https=(request.channel in self.config["ignore_requests"].keys()),
        )
        return message

    def todaybest(self, request):
        args = Parsing.Top(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1

        # query = request.arguments
        # if not query:
        #     query = self.users.get(request.channel)
        # message = ""
        # place = 1
        # query = re.sub("%..", " ", query)
        # tokens = [x.strip() for x in str(query).split(" ") if x.strip()]
        # if tokens[-1].isnumeric() and len(tokens[-1]) < 3:
        #     place = int(tokens.pop())
        #     if place <= 0:
        #         place = 1
        # query = " ".join(tokens)
        # if len(query) == 0:
        #     query = self.users.get(request.channel)
        message = ""

        user_data = self.osu.get_user_data(args["username"])
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
        if len(recent_plays) < args["index"] and args["index"] != 1:
            message += (
                "Requested place unavailable, falling back to best score of the day. "
            )
            args["index"] = 1
        score_data = recent_plays[args["index"] - 1]

        message += f"Today's score #{args['index']} for {username}: {self.score_info(score_data, remove_https=(request.channel in self.config['ignore_requests'].keys()))}"
        return message

    def ppcounter(self, request):
        return "not implenented PEEPEES"

        query = request.arguments
        if not query:
            return "usage: !pp [map id | recent] [mods]"
        query = " ".join([x.strip() for x in query.split(" ") if x.strip()])
        if query[0].lower() == "recent":
            query = self.osu.get_last_played(self.users.get(request.channel))
            if not query.ok or len(query.json()) == 0:
                return "Could not get recent score PEEPEES"
            map_id = str(query[0]["beatmap"]["id"])
            mods = str(query[0]["beatmap"]["id"])

    def req(self, request: Message, map_id):
        # return 'ChiconyBusiness Send map link to osu!pm'
        BEATMAP_URL = "https://osu.ppy.sh/b/"
        beatmap = self.osu.get_beatmap(map_id)
        if beatmap.ok:
            map_name = map_name_from_response(beatmap.json())
            message = f"{request.user} | [{BEATMAP_URL}{map_id} {map_name}]"
            response = self.osu.send_pm(self.users.get(request.channel), message)
            return f"{request.user} sent request: {map_name}"
        else:
            return "Seems like beatmap does not exist, are you sure dogQ"

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
    #         response = self.osu.send_pm(self.users.get(request.channel), message)
    #         return f"{user} sent request: {map_name}"
    #     else:
    #         return "Seems like beatmap does not exist, are you sure dogQ"


# regex for commands - '!command_name($| .*)'
