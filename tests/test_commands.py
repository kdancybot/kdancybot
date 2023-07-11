import unittest
import configparser

from kdancybot.Message import Message
from kdancybot.Commands import Commands


class TestCommands(unittest.TestCase):
    # def setUp(self):
    # 	self.message =
    def setUp(self):
        self.config = configparser.ConfigParser()
        self.config.read("config.ini")
        self.commands = Commands(self.config)
        self.username = next(iter(self.config["users"].keys()))
        self.msg = ":{username}!{username}@{username}.tmi.twitch.tv PRIVMSG #{sender} :{{message}}".format(
            username=self.username, sender="andrefq"
        )
        self.score_info_regex = (
            "https:\/\/osu.ppy.sh\/b\/[0-9]*.* - .* \[.*\] .*\*.*ago"
        )
        self.regexes = {
            "score_info": "https:\/\/osu.ppy.sh\/b\/[0-9]*.* - .* \[.*\] .*\*.*ago",
            "no_scores": "No scores for .{3,16} \(#([0-9]{1,8}|None)\) in last 24 hours",
        }
        self.messages = {
            "recent_no_args": Message(self.msg.format(message="!r")),
            "recent_name_only": Message(self.msg.format(message="!r andref")),
            "recent_name_count": Message(self.msg.format(message="!r andref 2")),
            "recent_count_name": Message(self.msg.format(message="!r 2 andref")),
            "recent_count_name_with_spaces": Message(
                self.msg.format(message="!r 2 m i s h a")
            ),
            "recent_invalid_name": Message(
                self.msg.format(message="!r super_dodster_727")
            ),
            "recentbest_no_args": Message(self.msg.format(message="!rb")),
            "recentbest_name_only": Message(self.msg.format(message="!rb andref")),
            "recentbest_name_count": Message(self.msg.format(message="!rb andref 4")),
            "recentbest_count_name": Message(self.msg.format(message="!rb 4 andref")),
            "recentbest_count_name_with_spaces": Message(
                self.msg.format(message="!rb 4 m i s h a")
            ),
            "recentbest_invalid_name": Message(
                self.msg.format(message="!rb super_dodster_727")
            ),
            "todaybest_no_args": Message(self.msg.format(message="!tb")),
            "todaybest_name_only": Message(self.msg.format(message="!tb andref")),
            "todaybest_name_count": Message(self.msg.format(message="!tb andref 2")),
            "todaybest_count_name": Message(self.msg.format(message="!tb 2 andref")),
            "todaybest_count_name_with_spaces": Message(
                self.msg.format(message="!tb 3 m i s h a ")
            ),
            "todaybest_invalid_name": Message(
                self.msg.format(message="!tb 3 super_dodster_727")
            ),
            "whatif_no_args": Message(self.msg.format(message="!whatif")),
            "whatif_pp_only": Message(self.msg.format(message="!whatif 727")),
            "whatif_pp_count": Message(self.msg.format(message="!whatif 727 4")),
            "whatif_count_pp": Message(self.msg.format(message="!whatif 4 727")),
            "whatif_pp_map": Message(self.msg.format(message="!whatif 727 658127")),
            "whatif_map_pp": Message(self.msg.format(message="!whatif 658127 727")),
            "whatif_invalid_arguments": Message(
                self.msg.format(message="!whatif 4 658127 727")
            ),
            "ppdiff_no_args": Message(self.msg.format(message="!ppdiff")),
            "ppdiff_one_name": Message(self.msg.format(message="!ppdiff woriks")),
            "ppdiff_one_name_with_spaces": Message(
                self.msg.format(message="!ppdiff m i s h a")
            ),
            "ppdiff_two_names": Message(
                self.msg.format(message="!ppdiff woriks on1x-")
            ),
            "ppdiff_two_names_with_spaces": Message(
                self.msg.format(message="!ppdiff woriks m i s h a")
            ),
            "ppdiff_two_names_with_spaces_extreme": Message(
                self.msg.format(message="!ppdiff [ s a s h a ] m i s h a")
            ),
        }

    def test_recent(self):
        good_tests = {
            "recent_no_args": Message(self.msg.format(message="!r")),
            "recent_name_only": Message(self.msg.format(message="!r andref")),
            "recent_name_count": Message(self.msg.format(message="!r andref 2")),
            "recent_count_name": Message(self.msg.format(message="!r 2 andref")),
            "recent_count_name_with_spaces": Message(
                self.msg.format(message="!r 2 m i s h a")
            ),
        }
        bad_tests = {
            "recent_invalid_name": Message(
                self.msg.format(message="!r super_dodster_727")
            )
        }

        for test in good_tests.values():
            result = self.commands.recent(test)
            with self.subTest(test=test):
                try:
                    self.assertRegex(result, self.regexes["score_info"])
                except AssertionError:
                    self.assertRegex(result, self.regexes["no_scores"])
        for test in bad_tests.values():
            self.assertTrue(self.commands.recent(test) == "Who is this Concerned")

    def test_recentbest(self):
        good_tests = {
            "recentbest_no_args": Message(self.msg.format(message="!rb")),
            "recentbest_name_only": Message(self.msg.format(message="!rb andref")),
            "recentbest_name_count": Message(self.msg.format(message="!rb andref 4")),
            "recentbest_count_name": Message(self.msg.format(message="!rb 4 andref")),
            "recentbest_count_name_with_spaces": Message(
                self.msg.format(message="!rb 4 m i s h a")
            ),
        }
        bad_tests = {
            "todaybest_invalid_name": Message(
                self.msg.format(message="!tb 3 super_dodster_727")
            ),
        }

        for test in good_tests.values():
            result = self.commands.recentbest(test)
            with self.subTest(test=test):
                try:
                    self.assertRegex(
                        result,
                        "Latest top score #[0-9]{1,3} for .{3,16} \(#([0-9]{1,8}|None)\): "
                        + self.regexes["score_info"],
                    )
                except AssertionError:
                    self.assertIs(result, "Bro's profile is wiped Sadge")
        for test in bad_tests.values():
            with self.subTest(test=test):
                self.assertTrue(
                    self.commands.recentbest(test) == "Unknown user MyHonestReaction"
                )

    def test_todaybest(self):
        good_tests = {
            "todaybest_no_args": Message(self.msg.format(message="!tb")),
            "todaybest_name_only": Message(self.msg.format(message="!tb andref")),
            "todaybest_name_count": Message(self.msg.format(message="!tb andref 2")),
            "todaybest_count_name": Message(self.msg.format(message="!tb 2 andref")),
            "todaybest_count_name_with_spaces": Message(
                self.msg.format(message="!tb 3 m i s h a ")
            ),
        }
        bad_tests = {
            "todaybest_invalid_name": Message(
                self.msg.format(message="!tb super_dodster_727")
            ),
        }

        for test in good_tests.values():
            result = self.commands.todaybest(test)
            with self.subTest(test=test):
                try:
                    self.assertRegex(
                        result,
                        "Today's score #[0-9]{1,3} for .{3,16} \(#([0-9]{1,8}|None)\): "
                        + self.regexes["score_info"],
                    )
                except AssertionError:
                    self.assertRegex(result, self.regexes["no_scores"])
        for test in bad_tests.values():
            with self.subTest(test=test):
                self.assertTrue(
                    self.commands.todaybest(test) == "Who is this Concerned"
                )

    def test_top(self):
        good_tests = {
            "top_no_args": Message(self.msg.format(message="!top")),
            "top_name_only": Message(self.msg.format(message="!top andref")),
            "top_name_count": Message(self.msg.format(message="!top andref 2")),
            "top_count_name": Message(self.msg.format(message="!top 2 andref")),
            "top_count_name_with_spaces": Message(
                self.msg.format(message="!top 3 m i s h a ")
            ),
        }
        bad_tests = {
            "top_invalid_name": Message(
                self.msg.format(message="!top super_dodster_727")
            ),
        }

        for test in good_tests.values():
            result = self.commands.top(test)
            with self.subTest(test=test):
                try:
                    self.assertRegex(
                        result,
                        "[0-9]{1,3}[a-z]{2} top score for .{3,16} \(#([0-9]{1,8}|None)\): "
                        + self.regexes["score_info"],
                    )
                except AssertionError:
                    self.assertRegex(result, self.regexes["no_scores"])
        for test in bad_tests.values():
            with self.subTest(test=test):
                self.assertTrue(self.commands.top(test) == "Who is this Concerned")
