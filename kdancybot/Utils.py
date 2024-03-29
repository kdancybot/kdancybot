from rosu_pp_py import Beatmap, Calculator
from datetime import datetime, timedelta, timezone
import json
import re
import logging
from math import ceil

logger = logging.getLogger(__name__)

Mods = {
    "NF": 1,
    "EZ": 2,
    "HT": 256,
    "HD": 8,
    "DT": 64,
    "NC": 576,
    "HR": 16,
    "FL": 1024,
    "SD": 32,
    "PF": 16384,
    "SO": 4096,
    "V2": 536870912,
}


class Map:
    def __init__(self, pp, map_id):
        self.pp = pp
        self.map_id = map_id


class ScoresToOvertake:
    def __init__(self, pp, count=1):
        self.pp = pp
        self.count = count


def username_from_response(response):
    username = response["username"]
    return username + " (#" + str(response["statistics"]["global_rank"]) + ")"


def map_name_from_response(score_data):
    # Very bad hack
    beatmap = score_data.get("beatmap", score_data)
    return f"{score_data['beatmapset']['artist']} - {score_data['beatmapset']['title']} [{beatmap['version']}]"


# returns pp value which user would need to get to get `goal_pp` on `scores_count` scores
def calculate_pp_values_to_overtake(pp_values: list, goal_pp, scores_count):
    # since there's no way to get scores outside of top 100 and take them into account
    # we clear space for `scores_count` plays to get 100 plays at most
    weighted = calculate_weighted(pp_values)
    weighted = weighted[: min(100 - scores_count, len(weighted))]
    wsum = sum(weighted)
    remainder = 0
    for i in range(len(weighted) - 1, 0, -1):
        wsum -= weighted[i]
        remainder += 0.95**scores_count * weighted[i]
        pp_needed = goal_pp - wsum - remainder
        # partial sum of geometric series with length of `scores_count` and starting index of i
        new_plays = pp_values[i - 1] * (1 - 0.95**scores_count) / (1 - 0.95)
        new_plays_weighted = new_plays * 0.95**i
        if new_plays_weighted > pp_needed:
            logger.debug(
                f"i: {i}, wsum: {wsum}, remainder: {remainder}, goal_pp: {goal_pp}, new_plays: {new_plays}, new_plays_weighted: {new_plays_weighted}"
            )
            return (pp_needed * (1 - 0.95) / (1 - 0.95**scores_count)) / 0.95**i
    return (
        (goal_pp - sum(weighted) * 0.95**scores_count)
        * (1 - 0.95)
        / (1 - 0.95**scores_count)
    )


def get_max_pp_value_for_scores_count(pp_value, count):
    if count <= 1:
        return pp_value
    if count <= 3:
        return round_up_to_hundred(pp_value)
    if count < 10:
        return round_up_to_hundred((1 + 0.02 * count) * pp_value)
    return round_up_to_hundred(1.2 * pp_value)


# returns dict with "count" and "pp" keys if calculated successfully
# returns dict with "error_code" and "error_desc" keys if calculation failed
def pp_to_overtake(top100, user_pp, goal_pp):
    if user_pp >= goal_pp:
        return {"error_code": 1, "error_desc": "Goal pp is already reached by user"}

    if len(top100) == 0:
        return {"error_code": 3, "error_desc": "User has no scores"}

    pp_values = [score["pp"] for score in top100]
    weighted = calculate_weighted(pp_values)
    wsum = sum(weighted)
    bonus_pp = user_pp - wsum

    # Here we make a guess that the highest pp score a player can get is
    # their top play + 25% rounded up to next hundred
    max_score_pp = round_up_to_hundred((pp_values[0] or 0) * 1.25)

    # if player gets 100 max_score_pp's and still doesn't get to goal pp
    if max_score_pp * 20 + bonus_pp < goal_pp:
        return {
            "error_code": 2,
            "error_desc": "User can't reach goal pp realistically",
        }

    for i in range(1, 101):
        predicted_pp = calculate_pp_values_to_overtake(pp_values, goal_pp - bonus_pp, i)
        if predicted_pp <= get_max_pp_value_for_scores_count(pp_values[0], i):
            logger.debug({"count": i, "pp": predicted_pp})
            return {"count": i, "pp": predicted_pp}

    return {
        "error_code": 2,
        "error_desc": "User can't reach goal pp realistically",
    }


def mods_to_num(mods):
    sum = 0
    for mod in mods:
        sum += int(Mods.get(mod, 0))
    return sum


def build_calculator(score_data):
    mods = mods_to_num(score_data["mods"])
    stats = score_data["statistics"]
    calc = Calculator(
        mode=0,
        mods=mods,
        n300=stats["count_300"],
        n100=stats["count_100"],
        n50=stats["count_50"],
        n_misses=stats["count_miss"],
        passed_objects=get_passed_objects(score_data),
        combo=score_data["max_combo"],
    )
    return calc


def get_passed_objects(score_data):
    stats = score_data["statistics"]
    return (
        stats["count_300"]
        + stats["count_100"]
        + stats["count_50"]
        + stats["count_miss"]
    )


# UNUSED
def get_objects_count(score_data):
    beatmap = score_data["beatmap"]
    return (
        beatmap["count_circles"] + beatmap["count_spinners"] + beatmap["count_sliders"]
    )


def generate_mods_payload(mods):
    payload = ""
    for mod in mods:
        if mod in Mods.keys():
            payload += "mods%5B%5D=" + mod + "&"
    if len(payload):
        payload = payload[:-1]
    return payload


def ordinal(n: int):
    if 11 <= (n % 100) <= 13:
        suffix = "th"
    else:
        suffix = ["th", "st", "nd", "rd", "th"][min(n % 10, 4)]
    return str(n) + suffix


def score_age(date: str) -> str:
    try:
        magnitudes = ["y", "mth", "d", "h", "min", "s"]
        diff = datetime.now(timezone.utc) - datetime.strptime(
            date, "%Y-%m-%dT%H:%M:%S%z"
        )
        orders = [
            diff.days // 365,
            diff.days // 30,
            diff.days,
            diff.seconds // 3600,
            diff.seconds // 60,
            diff.seconds,
        ]
        for i in range(len(orders)):
            if orders[i] > 0:
                return f"{orders[i]}{magnitudes[i]} ago"
    except Exception:
        pass
    return ""


def generate_mods_string(mods) -> str:
    return f" +{''.join(mods)}" if len(mods) else ""


def parse_beatmap_link(message):
    patterns = {
        "default": r"osu\.ppy\.sh\/beatmapsets\/(?P<set_id>[0-9]{1,7})\#(?P<mode>osu|taiko|fruits|mania)\/(?P<map_id>[0-9]{1,7})\+?(?P<mods>[ -~]*)",
        "short": r"osu.ppy.sh\/beatmaps\/(?P<map_id>[0-9]+)\+?(?P<mods>[ -~]*)",
        "even_shorter": r"(osu|old).ppy.sh\/b\/(?P<map_id>[0-9]+)\+?(?P<mods>[ -~]*)?",
    }

    for link_type, pattern in patterns.items():
        result = re.search(pattern, message)
        if result is not None:
            result = result.groupdict()

            result["mods"] = re.sub(
                r"[^A-Za-z]", "", 
                result.get("mods", "").upper()
            )
            result["mods"] = [
                result["mods"][i:i+2] for i in range(0, len(result["mods"]), 2)
            ]
            result["mods"] = [
                mod for mod in Mods.keys() if mod in result["mods"]
            ]
            return result

    return None


def upsert_scores(old_scores: list[Map], new_scores: list[Map]) -> list[Map]:
    lowest_pp = old_scores[-1].pp
    for score in new_scores:
        updated = False
        for i in range(len(old_scores)):
            if score.map_id == old_scores[i].map_id:
                old_scores[i].pp = max(score.pp, lowest_pp)
                updated = True
                break
        if not updated:
            old_scores.append(score)
    return old_scores


def get_bpm_multiplier(mods: list):
    return 1.5 if ("DT" in mods) or ("NC" in mods) else 0.75 if "HT" in mods else 1


def round_up_to_hundred(number):
    return (1 + (int(number) // 100)) * 100


def calculate_weighted(pp_values):
    return [0.95**i * float(pp_values[i]) for i in range(len(pp_values)) if pp_values[i]]

# NP Utils


def gm_get_acc_and_pp_for_fc(response):
    acc = max(ceil(response["gameplay"]["accuracy"]), 95)
    return acc, response["menu"]["pp"][str(acc)]


def sc_get_acc_and_pp_for_fc(response):
    acc = response["acc"]
    if acc < 90:
        return 90, response["osu_m90PP"]
    if acc < 95:
        return 95, response["osu_m95PP"]
    if acc < 96:
        return 96, response["osu_m96PP"]
    if acc < 97:
        return 97, response["osu_m97PP"]
    if acc < 98:
        return 98, response["osu_m98PP"]
    if acc < 99:
        return 99, response["osu_m99PP"]
    if acc < 99.9:
        return 99.9, response["osu_m99_9PP"]
    return 100, response["osu_mSSPP"]


# gosumemory
def convert_mods_to_list_gm(mods) -> list:
    if mods == "NM":
        return []
    return [mods[i:i+2] for i in range(0, len(mods), 2)]


def convert_gm_response_to_score_data(response):
    acc, pp = gm_get_acc_and_pp_for_fc(response)
    return {
        "accuracy": response["gameplay"]["accuracy"] / 100,
        "args": {
            "max_combo": response["menu"]["bm"]["stats"]["maxCombo"],  # map's max combo
            "pp": response["gameplay"]["pp"]["current"],
            "acc_for_fc": acc,
            "pp_for_fc": pp,
        },
        "attributes": {
            "star_rating": response["menu"]["bm"]["stats"]["fullSR"],
        },
        "beatmap": {
            "id": response["menu"]["bm"]["id"],
            "version": response["menu"]["bm"]["metadata"]["difficulty"],
            "status": "ranked",
        },
        "beatmapset": {
            "id": response["menu"]["bm"]["set"],
            "artist": response["menu"]["bm"]["metadata"]["artist"],
            "title": response["menu"]["bm"]["metadata"]["title"],
        },
        "created_at": "None",
        "max_combo": response["gameplay"]["combo"]["max"],  # current try's max combo
        "mods": convert_mods_to_list_gm(response["menu"]["mods"]["str"]),
        "statistics": {
            "count_300": response["gameplay"]["hits"]["300"],
            "count_100": response["gameplay"]["hits"]["100"],
            "count_50": response["gameplay"]["hits"]["50"],
            "count_miss": response["gameplay"]["hits"]["0"],
        },
        "pp": response["gameplay"]["pp"]["current"],
        "pp_if_fc": {
            95: response["menu"]["pp"]["95"],
            96: response["menu"]["pp"]["96"],
            97: response["menu"]["pp"]["97"],
            98: response["menu"]["pp"]["98"],
            99: response["menu"]["pp"]["99"],
            100: response["menu"]["pp"]["100"],
        },
        "map_data": response.get("mapData", "").encode()
    }


# stream companion
def convert_mods_to_list_sc(mods):
    mods.replace("SV2", "V2")
    return [mods[i:i+2] for i in range(0, len(mods), 2)]


def convert_sc_response_to_score_data(response):
    acc, pp = sc_get_acc_and_pp_for_fc(response)
    mods = "" if response["mods"] == "None" else "".join(response["mods"].split(","))
    return {
        "accuracy": response["acc"] / 100,
        "args": {
            "max_combo": response["maxCombo"],
            "pp": response["ppIfMapEndsNow"],
            "acc_for_fc": acc,
            "pp_for_fc": pp,
        },
        "attributes": {
            "star_rating": response["mStars"],
        },
        "beatmap": {
            "id": response["mapid"],
            "version": response["diffName"],
            "status": "ranked",
        },
        "beatmapset": {
            "id": response["mapsetid"],
            "artist": response["artistRoman"],
            "title": response["titleRoman"],
        },
        "created_at": "None",
        "max_combo": response["currentMaxCombo"],
        "mods": convert_mods_to_list_sc(mods),
        "statistics": {
            "count_300": response["c300"],
            "count_100": response["c100"],
            "count_50": response["c50"],
            "count_miss": response["miss"],
        },
        "pp": response["ppIfMapEndsNow"],
        "pp_if_fc": {
            95: response["osu_m95PP"],
            96: response["osu_m96PP"],
            97: response["osu_m97PP"],
            98: response["osu_m98PP"],
            99: response["osu_m99PP"],
            100: response["osu_mSSPP"],
        },
        "map_data": response.get("mapData", "").encode()
    }


# Two random identifying keys
def convert_np_response_to_score_data(response):
    if "menu" in response.keys():
        return convert_gm_response_to_score_data(response)
    elif "score" in response.keys():
        return convert_sc_response_to_score_data(response)


def pp_to_str(pp_value):
    return f"{int(float(pp_value) + .5)}pp"


def format_acc_and_pp(acc, pp_if_fc):
    return f"{acc}%: {pp_to_str(pp_if_fc)}"


def generate_pp_if_fc(score_data, accuracies):
    # For ease of predicting amount of 50s and 100s
    # it's assumed you can only get 100s or 300s
    LOWEST_ACC = 33.33

    result_data = dict()

    try:
        mods = mods_to_num(score_data["mods"])
        beatmap = Beatmap(bytes=score_data["map_data"])
        calc = Calculator(
            mode=0,
            mods=mods,
            combo=score_data["args"]["max_combo"],
        )
        perf = calc.performance(beatmap)
        all_objects = perf.difficulty.n_circles + perf.difficulty.n_sliders + perf.difficulty.n_spinners

        for acc in accuracies:
            n100 = int((100 - acc) / (100 - LOWEST_ACC) * all_objects)
            n300 = all_objects - n100
            calc.set_n300(n300)
            calc.set_n100(n100)
            perf = calc.performance(beatmap)
            result_data[acc] = perf.pp
    except Exception as e:
        pass
    return result_data


def generate_nppp_message(map_info, pps, accuracies):
    message = f"{map_info} | "
    pp_strings = []
    for acc in accuracies:
        if pps.get(acc) != None:
            pp_strings.append(format_acc_and_pp(acc, pps[acc]))
    
    return message + ", ".join([acc_pp for acc_pp in pp_strings])