#!/usr/bin/python3

import api.osuAPIv2
import Commands

from flask import Flask, request
import requests

app = Flask(__name__)

# enum Mods
# {
#     NoFail         = 1,
#     Easy           = 2,
#     TouchDevice    = 4,
#     Hidden         = 8,
#     HardRock       = 16,
#     SuddenDeath    = 32,
#     DoubleTime     = 64,
#     Relax          = 128,
#     HalfTime       = 256,
#     Nightcore      = 512, // Only set along with DoubleTime. i.e: NC only gives 576
#     Flashlight     = 1024,
#     Autoplay       = 2048,
#     SpunOut        = 4096,
#     Relax2         = 8192,    // Autopilot
#     Perfect        = 16384, // Only set along with SuddenDeath. i.e: PF only gives 16416
#     Key4           = 32768,
#     Key5           = 65536,
#     Key6           = 131072,
#     Key7           = 262144,
#     Key8           = 524288,
#     FadeIn         = 1048576,
#     Random         = 2097152,
#     Cinema         = 4194304,
#     Target         = 8388608,
#     Key9           = 16777216,
#     KeyCoop        = 33554432,
#     Key1           = 67108864,
#     Key3           = 134217728,
#     Key2           = 268435456,
#     ScoreV2        = 536870912,
#     Mirror         = 1073741824,
#     KeyMod = Key1 | Key2 | Key3 | Key4 | Key5 | Key6 | Key7 | Key8 | Key9 | KeyCoop,
#     FreeModAllowed = NoFail | Easy | Hidden | HardRock | SuddenDeath | Flashlight | FadeIn | Relax | Relax2 | SpunOut | KeyMod,
#     ScoreIncreaseMods = Hidden | HardRock | DoubleTime | Flashlight | FadeIn
# }


@app.route("/pp")
def pp():
    return Commands.pp(request)


@app.route("/recent")
def recent():
    return Commands.recent(request)


@app.route("/whatif")
def whatif():
    return Commands.whatif(request)


@app.route("/recentbest")
def recentbest():
    return Commands.recentbest(request)


@app.route("/todaybest")
def todaybest():
    return Commands.todaybest(request)


@app.route("/counter")
def ppcounter():
    return Commands.ppcounter(request)


@app.route("/request")
def req():
    return Commands.req(request)


@app.route("/rpp")
def rpp():
    return Commands.rpp(request)


# @app.route("/authorization")
# def auth():
#     code = request.args.get('code')
#     if not code:
#         return "No code :("
#     CODE = code
#     return code

if __name__ == "__main__":
    app.run()
