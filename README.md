<h1 align="center">kdancybot 🤖</h1>

osu! extension for twitch bots written in Python/Flask
## Supported commands 🤯
|Command|Feature|
|--|:--:|
|**link to a beatmap**|_requests_ a map to a streamer|
|**!r**               |shows _recent_ play of any player (defaults to streamer)|
|**!rb/!recentbest**  |shows most _recent_ play in player's _top 100_|
|**!tb/!todaybest**   |shows player's _best score of the day_|
|**!ppdiff**          |shows difference in pp values of two players|
|**!whatif**          |shows how many pp would streamer get for a certain pp score|

## Install 🛠️
### Extension installation ⚙️
**IMPORTANT:** This application should be ran on a PC with static IP, otherwise Twitch bot won't be able to send commands to extension 
```bash
git clone https://github.com/AndrefHub/kdancybot.git
cd kdancybot
python3 -m venv .
source bin/activate
pip install -r requirements.txt
flask run -p 7272 -h 0.0.0.0
```
### Twitch bot configuration 👨‍💻
Add commands to whatever twitch bot you are using

Example with Nightbot and request command:
```
$(urlfetch http://(IP | DOMAIN):7272/request?query=$(querystring)&user=$(user))
```
## TODO 💡
* [ ] Dockerize bot
* [x] Work with twitch API directly
* [ ] Add !np command (idk if it's possible)
* [ ] Indicate different roles on channel in request message (VIP, MOD, SUB etc.)
* [ ] Indicate map status (ranked, loved, graveyard etc.)
* [ ] Add database support
* [ ] Add !register command which will store users osu! account ids
* [ ] Add **me** alias for commands which require osu usernames
* [ ] Cache downloaded osu beatmaps
* [x] Support multiple twitch channels running in one instance
