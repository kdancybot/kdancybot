from Utils import *
import re
from rosu_pp_py import Beatmap, Calculator
import json
import api.osuv2ApiWrapper

### Methods working with osu!api, to be cropped and moved to Utils

osu = osuv2ApiWrapper()


def score_info(score_data):
    beatmap_attributes = osu.get_beatmap_attributes(
        score_data["beatmap"]["id"], score_data["mods"]
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

    map_data = osu.get_map_data(str(score_data["beatmap"]["id"]))
    objects_passed = get_passed_objects(score_data)
    all_objects = get_objects_count(score_data)
    n100 = int((score_data["statistics"]["count_100"] * all_objects) / objects_passed)
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
            " (" + str(int(perf.pp + 0.5)) + "pp for " + str(round(acc, 2)) + "% FC)"
        )
    if score_data["beatmap"]["status"] != "ranked":
        message += " if ranked"
    message = message.replace('"', '"')
    return message


def get_user_pair(lhs: str, rhs: str):
    tasks = [asyncio.ensure_future(get_user_data(u)) for u in [lhs, rhs]]
    users = asyncio.gather(*tasks)
    if users[0].ok and users[1].ok:
        return users


# TODO: REWRITE IT FFS
def get_users_from_query(query):
    query = re.sub("%..", " ", query)
    tokens = [x.strip() for x in query.split(" ") if x.strip()]

    query = " ".join(tokens)
    user_data = osu.get_user_data(DEFAULT_USER)
    other_data = osu.get_user_data(query)
    if user_data.ok and other_data.ok:
        return user_data, other_data, DEFAULT_USER, query

    for i in range(1, len(tokens)):
        user = " ".join(tokens[:i])
        other = " ".join(tokens[i:])
        user_data = osu.get_user_data(user)
        other_data = osu.get_user_data(other)
        if user_data.ok and other_data.ok:
            return user_data, other_data, user, other
    return None, None, None, None


def message_to_overtake(user_data, other_data):
    user_pp = user_data["statistics"]["pp"]
    goal_pp = other_data["statistics"]["pp"]
    top100 = osu.get_top_100(user_data["id"]).json()
    pp_value = pp_to_overtake(top100, user_pp, goal_pp)

    if pp_value < 0:
        return ""

    return f"{user_data['username']} needs to get a {int(pp_value + .5)}pp play to overtake {other_data['username']}"


###


def pp(request):
    message = ""
    user = request.args.get("user")
    other = request.args.get("other")
    query = request.args.get("query")

    if user and other:
        # return "Invalid user"
        user_data = osu.get_user_data(user)
        other_data = osu.get_user_data(other)
    elif query:
        user_data, other_data, user, other = get_users_from_query(query)

    if not (user_data and other_data and (user_data.ok and other_data.ok)):
        return "Could not find such user(s) NOOOO"

    user = username_from_response(user_data, user)
    other = username_from_response(other_data, other)

    userpp = user_data.json()["statistics"]["pp"]
    otherpp = other_data.json()["statistics"]["pp"]

    return message


def recent(request):
    message = ""
    user = request.args.get("user")
    if not user or user.isspace():
        user = DEFAULT_USER

    user = re.sub("%..", " ", user)
    # user = user.replace('%20', ' ')
    user = " ".join([x.strip() for x in str(user).split(" ") if x.strip()])
    if len(user) == 0:
        user = DEFAULT_USER
    user_data = osu.get_user_data(user)
    if not user_data.ok:
        return "Invalid user"

    recent_score = osu.get_last_played(user_data.json()["id"])
    if not recent_score.ok or len(recent_score.json()) == 0:
        return (
            "No scores for " + username_from_response(user_data) + " in last 24 hours"
        )

    score_data = recent_score.json()[0]
    message = score_info(score_data)
    return message


# TODO: add optional map id to whatif
def whatif(request):
    try:
        query = request.args.get("query")
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
    user_data = osu.get_user_data(user)
    message = username_from_response(user_data) + " needs to get a "
    user_data = user_data.json()
    full_pp = user_data["statistics"]["pp"]
    top100 = osu.get_top_100(user).json()
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


def recentbest(request):
    query = request.args.get("query")
    if not query or query.isspace():
        query = DEFAULT_USER

    query = re.sub("%..", " ", query)
    query = " ".join([x.strip() for x in str(query).split(" ") if x.strip()])
    if len(query) == 0:
        query = DEFAULT_USER
    user_data = osu.get_user_data(query)
    if not user_data.ok:
        return "Unknown user MyHonestReaction"

    username = username_from_response(user_data)
    user_data = user_data.json()
    full_pp = user_data["statistics"]["pp"]
    top100 = osu.get_top_100(user_data["id"]).json()
    score_data = max(top100, key=lambda score: score["created_at"])
    index = [
        i + 1
        for i in range(len(top100))
        if top100[i]["beatmap"]["id"] == score_data["beatmap"]["id"]
    ][0]

    message = "Latest top score #" + str(index) + " for " + username + ": "
    message += score_info(score_data)
    return message


def todaybest(request):
    query = request.args.get("query")
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
    user_data = osu.get_user_data(query)
    if not user_data.ok:
        return "Who is this Concerned"
    username = username_from_response(user_data)
    user_data = user_data.json()
    full_pp = user_data["statistics"]["pp"]
    recent_plays = sorted(
        osu.get_today_scores(user_data["id"]).json(),
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
    message += score_info(score_data)
    return message


def ppcounter(request):
    return "not implenented PEEPEES"

    query = request.args.get("query")
    if not query:
        return "usage: !pp [map id | recent] [mods]"
    query = " ".join([x.strip() for x in query.split(" ") if x.strip()])
    if query[0].lower() == "recent":
        query = osu.get_last_played(DEFAULT_USER)
        if not query.ok or len(query.json()) == 0:
            return "Could not get recent score PEEPEES"
        map_id = str(query[0]["beatmap"]["id"])
        mods = str(query[0]["beatmap"]["id"])


def req(request):
    # return 'ChiconyBusiness Send map link to osu!pm'
    BEATMAP_URL = "https://osu.ppy.sh/b/"
    query = request.args.get("query")
    if not query:
        return "RIPBOZO"
    try:
        beatmap = query.split("/")[-1]
        beatmap_id = int(beatmap)
    except:
        return "failed to parse beatmap id, are you sure it's correct?"

    message = f"{BEATMAP_URL}{beatmap_id}"
    response = osu.send_pm(DEFAULT_USER, message)
    return "Sent beatmap"
