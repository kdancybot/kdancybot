from kdancybot.api.osuAPI import osuAPIv2
from kdancybot.Utils import *

from rosu_pp_py import Beatmap, Calculator
import os


class osuAPIExtended(osuAPIv2):
    def __init__(self, config):
        super().__init__(config)

    def map_data(self, map_id):
        map_path = f"{self.config['map']['folder']}/{map_id}.osu"
        if os.path.isfile(map_path) and os.path.getsize(map_path):
            with open(map_path, "rb") as file:
                map_data = file.read()
        else:
            map_data = self.get_map_data(str(map_id)).content
            os.makedirs(self.config["map"]["folder"], exist_ok=True)
            with open(map_path, "wb") as file:
                file.write(map_data)
        return map_data

    def prepare_score_info(self, score_data):
        args = dict()

        beatmap_attributes = self.get_beatmap_attributes(
            score_data["beatmap"]["id"], generate_mods_payload(score_data["mods"])
        ).json()["attributes"]

        map_data = self.map_data(str(score_data["beatmap"]["id"]))
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

    def recent(self, args: dict):
        # data = dict()
        args["invalid_username"] = False
        args["no_scores_today"] = False
        args["index_too_big"] = False
        user_data = self.get_user_data(args["username"])
        if not user_data.ok:
            args["invalid_username"] = True
        else:
            args["username_rank"] = username_from_response(user_data.json())
            scores_func = (
                self.get_today_scores if args.get("pass-only") else self.get_last_played
            )
            recent_score = scores_func(user_data.json()["id"])
            if not recent_score.ok or len(recent_score.json()) == 0:
                args["no_scores_today"] = True
            else:
                if len(recent_score.json()) < args["index"]:
                    args["index_too_big"] = True
                    args["index"] = 1
                args["score_data"] = recent_score.json()[args["index"] - 1]
        return args
