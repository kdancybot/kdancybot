from kdancybot.Utils import *
import kdancybot.api.osuAPIExtended
from kdancybot.Message import Message
from kdancybot.Parsing import Parsing

import re
from rosu_pp_py import Beatmap, Calculator
import json
from datetime import datetime, timedelta
import logging
import traceback
import os

logger = logging.getLogger(__name__)
### Methods working with osu!api, to be cropped and moved to Utils


class Commands:
    def __init__(self, config):
        self.osu = kdancybot.api.osuAPIExtended.osuAPIExtended(config)
        self.config = config
        self.users = config["users"]

    def score_info(self, score_data, remove_https=False):
        args = self.osu.prepare_score_info(score_data)
        return self.osu.score_info_build(score_data, args, remove_https)

    def map_info(self, score_data, remove_https=False):
        args = self.osu.prepare_score_info(score_data)
        return self.osu.map_info_build(score_data, args, remove_https)

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
        logger.debug(f"'{query}'")
        logger.debug(f"{tokens}")

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
            message = f"{username_from_response(user_data)} is {round(userpp - otherpp, 1)}pp ahead of {username_from_response(other_data)}. {self.message_to_overtake(other_data, user_data)}"
        else:
            message = f"{username_from_response(user_data)} is {round(otherpp - userpp, 1)}pp behind {username_from_response(other_data)}. {self.message_to_overtake(user_data, other_data)}"
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

    def recent(self, request):
        args = Parsing.Recent(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        # message = ""

        args = self.osu.recent(args)
        if args["invalid_username"]:
            return "Who is this Concerned"

        if args["no_scores_today"]:
            return f"No scores for {args['username_rank']} in last 24 hours"

        # score_data = recent_score.json()[args["actual_index"] - 1]
        message = self.score_info(
            args["score_data"],
            remove_https=request.channel in self.config["ignore_requests"].keys(),
        )
        return message

    def recent_played(self, request):
        args = Parsing.Recent(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        # message = ""

        args = self.osu.recent(args)
        if args["invalid_username"]:
            return "Who is this Concerned"

        if args["no_scores_today"]:
            return f"No scores for {args['username_rank']} in last 24 hours"

        # score_data = recent_score.json()[args["actual_index"] - 1]
        message = self.map_info(
            args["score_data"],
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

        message += f"{ordinal(args['index'])} top score for {username}: "
        message += self.score_info(
            score_data,
            remove_https=(request.channel in self.config["ignore_requests"].keys()),
        )
        return message

    def whatif(self, request):
        args = Parsing.Whatif(
            request.arguments, self.osu, username=self.users.get(request.channel)
        )

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
        message += f"{round(args['pp'], 1)}pp score{'s' if args['count'] > 1 else ''}"
        if args["map_id"] > 0:
            try:
                map_response = self.osu.get_beatmap(args["map_id"])
                map_name = map_name_from_response(map_response.json())
                message += " on " + map_name
            except:
                logger.warning(traceback.format_exc())
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
            f"(#{user['statistics']['global_rank']}, #{user['statistics']['country_rank']}{user['country_code']})"
            if isinstance(user["statistics"]["global_rank"], int)
            else "",
            f"{user['statistics']['pp']}pp",
        ]
        message = " ".join([part for part in message_parts if part])
        return message

    def req(self, request: Message, map_info: dict):
        BEATMAP_URL = "https://osu.ppy.sh/b/"
        beatmap = self.osu.get_beatmap(map_info["map_id"])
        beatmap_attributes = self.osu.get_beatmap_attributes(
            map_info["map_id"], generate_mods_payload(map_info.get("mods", ""))
        ).json()["attributes"]
        if beatmap.ok:
            bpm = int(
                (
                    beatmap.json().get("bpm", 0)
                    * (
                        1.5
                        if ("DT" in map_info["mods"]) or ("NC" in map_info["mods"])
                        else 0.75
                        if "HT" in map_info["mods"]
                        else 1
                    )
                )
                + 0.5
            )
            mods = f"{'+' if map_info['mods'] else ''}{''.join(map_info['mods'])}"
            map_name = map_name_from_response(beatmap.json())
            message_parts = [
                f"{request.user} |",
                f"[{BEATMAP_URL}{map_info['map_id']}",
                f"{map_name}",
                f"{mods}",
                f"({round(beatmap_attributes['star_rating'], 2)}*,",
                f"{bpm}BPM)]",
            ]
            message = " ".join([part for part in message_parts if part])
            # message = f"{request.user} | [{BEATMAP_URL}{map_info['map_id']} {map_name} ({beatmap_attributes['meme']})]"
            response = self.osu.send_pm(self.users.get(request.channel), message)
            return f"{request.user} sent request: {map_name} {mods}"
        else:
            return "Seems like beatmap does not exist, are you sure dogQ"


# regex for commands - '!command_name($| .*)'
