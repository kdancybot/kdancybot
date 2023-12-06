from kdancybot.Utils import *
import kdancybot.api.osuAPIExtended
import kdancybot.api.np
from kdancybot.Message import Message
from kdancybot.Parsing import Parsing
from kdancybot.db.Models import Twitch
from kdancybot.RoutineBuilder import start_routines

import re
import logging
import traceback

logger = logging.getLogger(__name__)

class Commands:
    def __init__(self, config):
        self.osu = kdancybot.api.osuAPIExtended.osuAPIExtended(config)
        self.config = config
        self.users = None
        self.routines = None

    # Only this method should be used for creating class' instances
    # The reason is async function `start_routines` cannot be ran
    # in constructor (Yes, I know, it's not really a good solution)
    @classmethod
    async def Instance(cls, config):
        self = cls(config)
        await self.start_routines()
        return self

    async def update_users(self):
        self.users = Twitch.GetUsersDict()
        logger.info("Updating users")

    async def start_routines(self):
        if not self.routines:
            self.routines = await start_routines(
                {"func": self.update_users, "delay": 60}
            )

    async def score_info(self, score_data, remove_https=False):
        score_data["args"] = self.osu.prepare_score_info(score_data)
        return self.osu.score_info_build(score_data, remove_https)

    async def map_info(self, score_data, remove_https=False):
        return self.osu.map_info_build(score_data, remove_https)

    # def get_user_pair(lhs: str, rhs: str):
    #     tasks = [asyncio.ensure_future(get_user_data(u)) for u in [lhs, rhs]]
    #     users = asyncio.gather(*tasks)
    #     if users[0].ok and users[1].ok:
    #         return users

    # TODO: REWRITE IT FFS
    async def get_users_from_query(self, query, request):
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

    async def prepare_ppdiff_message(self, user_data, other_data):
        userpp = user_data["statistics"]["pp"]
        otherpp = other_data["statistics"]["pp"]
        # username = username_from_response(user_data)

        if userpp > otherpp:
            message = f"{username_from_response(user_data)} is {round(userpp - otherpp, 1)}pp ahead of {username_from_response(other_data)}. {await self.message_to_overtake(other_data, user_data)}"
        else:
            message = f"{username_from_response(user_data)} is {round(otherpp - userpp, 1)}pp behind {username_from_response(other_data)}. {await self.message_to_overtake(user_data, other_data)}"
        return message

    async def message_to_overtake(self, user_data, other_data):
        format_string = "{username} needs to get {count} {pp}pp play{'s' if count > 1 else ''} to overtake {other_data['username']}"
        user_pp = user_data["statistics"]["pp"]
        goal_pp = other_data["statistics"]["pp"]
        top100 = self.osu.get_top_100(user_data["id"]).json()
        scores = pp_to_overtake(top100, user_pp, goal_pp)

        if scores.get("error_code", 0):
            return ""
        count = scores["count"]

        return f"{user_data['username']} needs to get {count if count > 1 else 'a'} {int(scores['pp'] + .5)}pp play{'s' if count > 1 else ''} to overtake {other_data['username']}"

    async def ppdiff(self, request):
        message = ""
        query = request.arguments

        user_data, other_data, user, other = await self.get_users_from_query(query, request)

        if not (user_data and other_data and (user_data.ok and other_data.ok)):
            return "Could not find such user(s) NOOOO"

        message = await self.prepare_ppdiff_message(user_data.json(), other_data.json())
        return message

    async def recent(self, request):
        args = Parsing.Recent(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)

        args = self.osu.recent(args)
        if args["invalid_username"]:
            return "Who is this Concerned"

        if args["no_scores_today"]:
            return f"No scores for {args['username_rank']} in last 24 hours"

        message = await self.score_info(
            args["score_data"],
            remove_https=True
        )
        return message

    async def recent_played(self, request):
        args = Parsing.Recent(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)

        args = self.osu.recent(args)
        if args["invalid_username"]:
            return "Who is this Concerned"

        if args["no_scores_today"]:
            return f"No scores for {args['username_rank']} in last 24 hours"

        message = await self.map_info(
            args["score_data"],
            remove_https=True
        )
        return message

    async def now_playing_map(self, request):
        try:
            response = kdancybot.api.np.NPClient.get_np(request.channel).json()
            if response.get("error"):
                logger.info("NP: error from server for user {}: {}".format(request.channel, response))
                raise Exception()
        except Exception as e:
            logger.info(str(e))
            return self.recent_played(request)

        score_data = convert_np_response_to_score_data(response)

        message = await self.map_info(
            score_data,
            remove_https=True
        )
        return message

    async def now_playing(self, request):
        try:
            response = kdancybot.api.np.NPClient.get_np(request.channel).json()
            if response.get("error"):
                logger.info("NP: error from server for user {}: {}".format(request.channel, response))
                raise Exception()
        except Exception as e:
            logger.info(str(e))
            return await self.recent_played(request)

        score_data = convert_np_response_to_score_data(response)
        score_data["args"] = self.osu._prepare_score_info(
            score_data,
            score_data["map_data"]
        )

        if score_data["max_combo"]:
            message = self.osu.score_info_build(
                score_data,
                remove_https=True
            )
        else:
            message = await self.map_info(
                score_data,
                remove_https=True
            )
        return message

    async def now_playing_pp(self, request):
        try:
            response = kdancybot.api.np.NPClient.get_np(request.channel).json()
            if response.get("error"):
                logger.info("NP: error from server for user {}: {}".format(request.channel, response))
                raise Exception()
        except Exception as e:
            logger.info(str(e))
            return ""

        score_data = convert_np_response_to_score_data(response)
        score_data["args"] = self.osu._prepare_score_info(
            score_data,
            score_data["map_data"]
        )
        pp_if_fc = generate_pp_if_fc(score_data, [95, 98, 100])
        response_format = "{map_info} | {pp95}, {pp98}, {pp100}"
        parts = {
            "map_info": await self.map_info(
                score_data,
                remove_https=True
            ),
            "pp95": pp_if_fc['95'],
            "pp98": pp_if_fc['98'],
            "pp100": pp_if_fc['100']
        }
        message = response_format.format(**parts)
        return message

    async def top(self, request):
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
        top100 = self.osu.get_top_100(user_data["id"]).json()
        if len(top100) == 0:
            return f"No scores for {username} in last 24 hours"
        if len(top100) < args["index"] and args["index"] != 1:
            # message += "Requested place unavailable, falling back to #1. "
            args["index"] = 1
        score_data = top100[args["index"] - 1]

        message += f"{ordinal(args['index'])} top score for {username}: "
        message += await self.score_info(
            score_data,
            remove_https=True
        )
        return message

    async def whatif(self, request):
        args = Parsing.Whatif(
            request.arguments,
            self.osu,
            username=self.users.get(request.channel)
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

        message = f"Prayge If {user_data['username']} gets "
        message += f"{args['count']} " if args["count"] > 1 else ""
        message += f"{round(args['pp'], 1)}pp score{'s' if args['count'] > 1 else ''}"
        if args["map_id"] > 0:
            try:
                map_response = self.osu.get_beatmap(args["map_id"])
                map_name = map_name_from_response(map_response.json())
                message += " on " + map_name
            except Exception:
                logger.warning(traceback.format_exc())
        message += f", he would be at {round(new_pp, 1):}" + "pp ("
        message += f"{round(new_pp - full_pp, 1):+} pp)"
        return message

    async def recentbest(self, request):
        format_string = "Latest top score #{index} for {username}: {score_data}"
        args = Parsing.Top(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1

        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Unknown user MyHonestReaction"

        user_data = user_data.json()
        username = username_from_response(user_data)
        top100 = self.osu.get_top_100(user_data["id"]).json()

        if len(top100) == 0:
            return "Profile is nonexistent Sadge"
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

        data = {
            "index": index,
            "username": username,
            "score_data": await self.score_info(
                score_data,
                remove_https=True
            ),
        }
        return format_string.format(**data)

    async def todaybest(self, request):
        format_string = "Today's score #{index} for {username}: {score_data}"
        args = Parsing.Top(request.arguments)
        if not args.get("username"):
            args["username"] = self.users.get(request.channel)
        if not args.get("index"):
            args["index"] = 1

        user_data = self.osu.get_user_data(args["username"])
        if not user_data.ok:
            return "Who is this Concerned"
        user_data = user_data.json()
        username = username_from_response(user_data)
        recent_plays = sorted(
            self.osu.get_today_scores(user_data["id"]).json(),
            key=lambda score: float(0 if score["pp"] is None else score["pp"]),
            reverse=True,
        )
        if len(recent_plays) == 0:
            return "No scores for " + username + " in last 24 hours Sadge"
        if len(recent_plays) < args["index"] and args["index"] != 1:
            # message += (
            #     "Requested place unavailable, falling back to best score of the day. "
            # )
            args["index"] = 1
        score_data = recent_plays[args["index"] - 1]

        data = {
            "index": args["index"],
            "username": username,
            "score_data": await self.score_info(
                score_data,
                remove_https=True
            ),
        }

        return format_string.format(**data)

    async def profile(self, request: Message):
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
            f"{round(user['statistics']['pp'], 1)}pp",
        ]
        message = " ".join([part for part in message_parts if part])
        return message

    async def req(self, request: Message, map_info: dict):
        BEATMAP_URL = "https://osu.ppy.sh/b/"
        beatmap = self.osu.get_beatmap(map_info["map_id"])
        beatmap_attributes = self.osu.get_beatmap_attributes(
            map_info["map_id"], generate_mods_payload(map_info.get("mods", ""))
        ).json()["attributes"]
        if beatmap.ok:
            bpm = int(
                beatmap.json().get("bpm", 0) * get_bpm_multiplier(map_info["mods"])
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
            response = self.osu.send_pm(
                self.users.get(request.channel),
                message
            )
            return f"Sent request: {map_name} {mods}"
        else:
            return "Seems like beatmap does not exist, are you sure dogQ"



# regex for commands - '!command_name($| .*)'
