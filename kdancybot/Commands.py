from kdancybot.Utils import *
import kdancybot.api.osuAPI
from kdancybot.Message import Message
from kdancybot.Parsing import Parsing

import re
from rosu_pp_py import Beatmap, Calculator
import json
from datetime import datetime, timedelta
import logging
import traceback
import os


### Methods working with osu!api, to be cropped and moved to Utils


class Commands:
    def __init__(self, config):
        self.osu = kdancybot.api.osuAPI.osuAPIv2(config)
        self.config = config
        self.users = config["users"]

    def get_map_data(self, map_id):
        map_path = f"{self.config['map']['folder']}/{map_id}.osu"
        if os.path.isfile(map_path) and os.path.getsize(map_path):
            with open(map_path, "rb") as file:
                map_data = file.read()
        else:
            map_data = self.osu.get_map_data(str(map_id)).content
            os.makedirs(self.config['map']['folder'], exist_ok=True)
            with open(map_path, "wb") as file:
                file.write(map_data)
        return map_data

    def prepare_score_info(self, score_data):
        args = dict()

        beatmap_attributes = self.osu.get_beatmap_attributes(
            score_data["beatmap"]["id"], generate_mods_payload(score_data["mods"])
        ).json()["attributes"]

        map_data = self.get_map_data(str(score_data["beatmap"]["id"]))
        objects_passed = get_passed_objects(score_data)
        all_objects = get_objects_count(score_data)
        n100 = (score_data["statistics"]["count_100"] * all_objects) // objects_passed
        n50 = (score_data["statistics"]["count_50"] * all_objects) // objects_passed
        n300 = all_objects - n100 - n50
        acc = 100 * (n300 + n100 / 3 + n50 / 6) / all_objects

        calc = build_calculator(score_data)
        beatmap = Beatmap(bytes=map_data)

        curr_perf = calc.performance(beatmap)
        calc.set_passed_objects(all_objects)
        calc.set_n300(n300)
        calc.set_n100(n100)
        calc.set_n50(n50)
        calc.set_n_misses(0)
        calc.set_combo(beatmap_attributes["max_combo"])
        perf = calc.performance(beatmap)

        args["max_combo"] = beatmap_attributes["max_combo"]
        args["star_rating"] = beatmap_attributes["star_rating"]
        args["curr_perf"] = curr_perf
        args["perf"] = perf
        args["acc"] = acc
        return args

    def score_info_build(self, score_data, args, remove_https=False):
        acc = args["acc"]
        message_parts = [
            f"{'https://' if not remove_https else ''}osu.ppy.sh/b/{score_data['beatmap']['id']}",  # map link
            map_name_from_response(score_data),  # map name
            f"{round(args['star_rating'], 2)}*",  # star rating
            generate_mods_string(score_data["mods"]),  # mods | None
            f"{round(score_data['accuracy'] * 100, 2)}%",  # accuracy
            f"{score_data['max_combo']}/{args['max_combo']}x"  # combo or "FC"
            if args["max_combo"] != score_data["max_combo"]
            else "FC",
            f"{score_data['statistics']['count_miss']}xMiss"  # misses | None
            if score_data["statistics"]["count_miss"]
            else "",
            f"{int((score_data['pp'] if score_data['pp'] else args['curr_perf'].pp) + .5)}pp",
            f"({int(args['perf'].pp + 0.5)}pp for {f'{round(acc, 2)}% FC' if acc != 100 else 'SS'})"
            if args["max_combo"] >= score_data["max_combo"] + 10
            or score_data["statistics"]["count_miss"]
            else "",
            "if ranked" if score_data["beatmap"]["status"] != "ranked" else "",
            f"{score_age(score_data['created_at'])} ago",
        ]
        # message = message.replace('"', "")
        message = " ".join([part for part in message_parts if part])
        return message

    def score_info(self, score_data, remove_https=False):
        args = self.prepare_score_info(score_data)
        return self.score_info_build(score_data, args, remove_https)

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

    def ppdiff(self, request):
        message = ""
        query = request.arguments

        user_data, other_data, user, other = self.get_users_from_query(query, request)

        if not (user_data and other_data and (user_data.ok and other_data.ok)):
            return "Could not find such user(s) NOOOO"

        message = self.prepare_ppdiff_message(user_data.json(), other_data.json())
        return message

    def recent_request(self, request):
        pass

    def recent(self, request):
        args = Parsing.Recent(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1
        message = ""

        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Who is this Concerned"

        scores_func = (
            self.osu.get_today_scores
            if args.get("pass-only")
            else self.osu.get_last_played
        )
        recent_score = scores_func(user_data.json()["id"])
        if not recent_score.ok or len(recent_score.json()) == 0:
            return (
                "No scores for "
                + username_from_response(user_data.json())
                + " in last 24 hours"
            )
            args["actual_index"] = 0
        elif len(recent_score.json()) < args["index"]:
            message += "Requested place unavailable, falling back to most recent. "
            args["actual_index"] = 1
        else:
            args["actual_index"] = args["index"]

        score_data = recent_score.json()[args["actual_index"] - 1]
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

    def whatif(self, request):
        args = Parsing.Whatif(request.arguments)

        if not args.get("pp"):
            return "Invalid arguments Tssk"

        user = self.users.get(request.channel)
        user_data = self.osu.get_user_data(user)
        user_data = user_data.json()
        full_pp = user_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user).json()
        pp_values = [Map(score["pp"], score["beatmap"]["id"]) for score in top100]
        weighted = [0.95**i * pp_values[i].pp for i in range(len(pp_values))]
        wsum = sum(weighted)
        bonus_pp = full_pp - wsum
        new_scores = [
            Map(args["pp"], args["map_id"] - i * 5000000) for i in range(args["count"])
        ]

        upsert_scores(pp_values, new_scores)
        pp_values.sort(reverse=True, key=lambda x: x.pp)
        pp_values = pp_values[:100]
        weighted = [0.95**i * pp_values[i].pp for i in range(len(pp_values))]
        wsum = sum(weighted)
        new_pp = wsum + bonus_pp

        message = "Prayge If " + user_data["username"] + " gets "
        message += f"{args['count']} " if args["count"] > 1 else ""
        message += str(args["pp"]) + f"pp score{'s' if args['count'] > 1 else ''}"
        if args["map_id"] > 0:
            try:
                map_response = self.osu.get_beatmap(args["map_id"])
                map_name = map_name_from_response(map_response.json())
                message += " on " + map_name
            except:
                logging.warning(traceback.format_exc())
        message += f", he would be at {round(new_pp, 1):}" + "pp ("
        message += f"{round(new_pp - full_pp, 1):+} pp)"
        return message

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

    def profile(self, request: Message):
        args = Parsing.Profile(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel, 2)
        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Who is this Concerned"
        user = user_data.json()

        message_parts = [
            f"https://osu.ppy.sh/u/{user['id']}",
            f"{user['username']}",
            f"(#{user['statistics']['global_rank']}, #{user['statistics']['country_rank']}{user['country_code']})" if isinstance(user['statistics']['global_rank'], int) else "",
            f"{user['statistics']['pp']}pp"
        ]
        message = ' '.join([part for part in message_parts if part])
        return message

    def req(self, request: Message, map_id):
        BEATMAP_URL = "https://osu.ppy.sh/b/"
        beatmap = self.osu.get_beatmap(map_id)
        if beatmap.ok:
            map_name = map_name_from_response(beatmap.json())
            message = f"{request.user} | [{BEATMAP_URL}{map_id} {map_name}]"
            response = self.osu.send_pm(self.users.get(request.channel), message)
            return f"{request.user} sent request: {map_name}"
        else:
            return "Seems like beatmap does not exist, are you sure dogQ"


# regex for commands - '!command_name($| .*)'
