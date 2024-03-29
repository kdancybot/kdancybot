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
            if self.get_beatmap(map_id).json()["status"].lower() in [
                "ranked",
                "approved",
                "loved",
            ]:
                os.makedirs(self.config["map"]["folder"], exist_ok=True)
                with open(map_path, "wb") as file:
                    file.write(map_data)
        return map_data

    def prepare_score_info(self, score_data):
        map_data = self.map_data(str(score_data["beatmap"]["id"]))
        return self._prepare_score_info(score_data, map_data)

    def _prepare_score_info(self, score_data, map_data):
        args = dict()
        try:
            args["max_combo"] = score_data["args"]["max_combo"]
            args["star_rating"] = score_data["attributes"]["star_rating"]
        except Exception:
            pass

        try:
            beatmap = Beatmap(bytes=map_data)
            calc = Calculator(mods=mods_to_num(score_data["mods"]))
            perf = calc.performance(beatmap)

            args["max_combo"] = perf.difficulty.max_combo
            args["star_rating"] = perf.difficulty.stars

            calc = build_calculator(score_data)
            curr_perf = calc.performance(beatmap)

            objects_passed = get_passed_objects(score_data)
            all_objects = perf.difficulty.n_circles + perf.difficulty.n_sliders + perf.difficulty.n_spinners
            if objects_passed:
                n100 = (score_data["statistics"]["count_100"] * all_objects) // objects_passed
                n50 = (score_data["statistics"]["count_50"] * all_objects) // objects_passed
            else:
                n100 = 0
                n50 = 0
            n300 = all_objects - n100 - n50
            acc = 100 * (n300 + n100 / 3 + n50 / 6) / all_objects

            calc.set_passed_objects(all_objects)
            calc.set_n300(n300)
            calc.set_n100(n100)
            calc.set_n50(n50)
            calc.set_n_misses(0)
            calc.set_combo(args["max_combo"])
            perf = calc.performance(beatmap)

            args["pp"] = curr_perf.pp
            args["pp_for_fc"] = perf.pp
            args["acc_for_fc"] = acc

        except Exception as e:
            pass
        finally:
            return args

    def build_acc_n_combo(self, combo, max_combo, acc, **kwargs):
        if acc >= 100 and combo == max_combo:
            return "SS"
        else:
            format_string = "{acc} {combo}"
            data = {
                "acc": f"{round(acc, 2)}%",
                # if for some reason we get max_combo lower than combo
                # we don't write max_combo to avoid confusions
                "combo": (
                    "FC" if combo == max_combo else
                    f"{combo}x" if combo > max_combo
                    else f"{combo}/{max_combo}x"
                )
            }
            return format_string.format(**data)

    def build_misses(self, misses, **kwargs):
        if misses == 0:
            return ""
        else:
            format_string = "{misses}xMiss"
            data = {"misses": misses}
            return format_string.format(**data)

    def build_pp_if_fc(self, acc_if_fc, pp_if_fc, combo, max_combo, misses, **kwargs):
        if combo > max_combo - 10 and misses == 0:
            return ""
        else:
            format_string = "({pp}pp for {acc})"
            data = {
                "pp": int(pp_if_fc + 0.5),
                "acc": self.build_acc_n_combo(0, 0, acc_if_fc),
            }
            return format_string.format(**data)

    def score_info_build(self, score_data, remove_https=False):
        format_string = (
            "{map_info} {acc_n_combo} {misses} {pp} {pp_if_fc} {if_ranked} {score_age}"
        )
        data = {
            "combo": score_data["max_combo"],
            "max_combo": score_data["args"]["max_combo"],
            "acc": score_data["accuracy"] * 100,
            "pp": score_data["pp"] if score_data["pp"] else score_data["args"]["pp"],
            "misses": score_data["statistics"]["count_miss"],
            "acc_if_fc": score_data["args"]["acc_for_fc"],
            "pp_if_fc": score_data["args"]["pp_for_fc"],
            "status": score_data["beatmap"]["status"],
            "created_at": score_data["created_at"],
        }
        parts = {
            "map_info": self.map_info_build(score_data, remove_https),
            "acc_n_combo": self.build_acc_n_combo(**data),
            "misses": self.build_misses(**data),
            "pp": f"{int(data['pp'] + .5)}pp",
            "pp_if_fc": self.build_pp_if_fc(**data),
            "if_ranked": "if ranked"
            if data["status"] not in ["ranked", "approved"]
            else "",
            "score_age": f"{score_age(data['created_at'])}",
        }
        return format_string.format(**parts)

    def nppp_build(self, score_data, remove_https=False):
        format_string = (
            "{map_info} {acc_n_combo} {misses} {pp} {pp_if_fc} {if_ranked}"
        )
        data = {
            "combo": score_data["max_combo"],
            "max_combo": score_data["args"]["max_combo"],
            "acc": score_data["accuracy"] * 100,
            "pp": score_data["pp"] if score_data["pp"] else score_data["args"]["pp"],
            "misses": score_data["statistics"]["count_miss"],
            "acc_if_fc": score_data["args"]["acc_for_fc"],
            "pp_if_fc": score_data["args"]["pp_for_fc"],
            "status": score_data["beatmap"]["status"],
            "created_at": score_data["created_at"],
        }
        parts = {
            "map_info": self.map_info_build(score_data, remove_https),
            "acc_n_combo": self.build_acc_n_combo(**data),
            "misses": self.build_misses(**data),
            "pp": f"{int(data['pp'] + .5)}pp",
            "pp_if_fc": self.build_pp_if_fc(**data),
            "if_ranked": "if ranked"
            if data["status"] not in ["ranked", "approved"]
            else "",
        }
        return format_string.format(**parts)

    def map_info_build(self, score_data, remove_https=False):
        format_string = "{link} {map_name} {star_rating} {mods}"
        link = ""
        if score_data['beatmap'].get('id'):
            link = f"{'https://' if not remove_https else ''}osu.ppy.sh/b/{score_data['beatmap'].get('id')}"
        elif score_data.get('beatmapset', {}).get('id'):
            link = f"{'https://' if not remove_https else ''}osu.ppy.sh/beatmapsets/{score_data['beatmapset'].get('id')}"
        data = {
            "link": link,
            "map_name": map_name_from_response(score_data),
            "star_rating": (
                f"{round(score_data['args']['star_rating'], 2)}*" 
                if score_data['args']['star_rating'] > 0 else ""
            ),
            "mods": generate_mods_string(score_data["mods"]),
        }
        return format_string.format(**data)

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
                args["score_data"]["attributes"] = self.get_beatmap_attributes(
                    args["score_data"]["beatmap"]["id"],
                    generate_mods_payload(args["score_data"]["mods"])
                ).json()["attributes"]
        return args
