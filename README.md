<h1 align="center">kdancybot 🤖</h1>

osu! chatbot for Twitch written in Python

## Supported commands 🤯

* **!request**    (requests a map to a streamer)
* **!recent**     (shows recent play of any player (defaults to streamer))
* **!recentbest** (shows most recent play in player's top 100)
* **!todaybest**  (shows player's best score of the day)
* **!ppdiff**     (shows difference in pp values of two players)
* **!whatif**     (shows how many pp would streamer get for a certain pp score)
* **!top**        (shows top play of any player (defaults to streamer))
* **!profile**    (shows profile (defaults to streamer))

## Install 🛠️
### Application installation ⚙️
**IMPORTANT:** If you want to use it, you can register on [kdancy.ru](https://kdancy.ru) (soon™) to use all of it's features
```bash
git clone https://github.com/AndrefHub/kdancybot.git
cd kdancybot
python3 -m venv .
source bin/activate
pip install -r requirements.txt
./run # <- this command should be ran as **root** or through **sudo**
```

## TODO 💡
* [ ] Dockerize bot
* [x] Work with twitch API directly
* [x] Add !np command (idk if it's possible)
* [ ] Indicate different roles on channel in request message (VIP, MOD, SUB etc.)
* [ ] Indicate map status (ranked, loved, graveyard etc.)
* [ ] Add database support
* [ ] Add !register command which will store users osu! account ids
* [ ] Add **me** alias for commands which require osu usernames
* [x] Cache downloaded osu beatmaps
* [x] Support multiple twitch channels running in one instance

