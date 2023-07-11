import unittest

from kdancybot.Message import Message

class TestMessage(unittest.TestCase):
	# def setUp(self):
	# 	self.message = 
	def test_command(self):
		text = "@badge-info=;badges=broadcaster/1;client-nonce=f98caa3e90522fc50eb7b71cd84c64a9;color=#1E90FF;display-name=Andrefq;emotes=;first-msg=0;flags=;id=521f9ac0-855b-4192-9671-45d8b1357257;mod=0;returning-chatter=0;room-id=156259639;subscriber=0;tmi-sent-ts=1688997911164;turbo=0;user-id=156259639;user-type= :andrefq!andrefq@andrefq.tmi.twitch.tv PRIVMSG #andrefq :!rb andref 72"
		message = Message(text)
		self.assertEqual(message.type, "PRIVMSG")
		self.assertEqual(message.user, "andrefq")
		self.assertEqual(message.channel, "andrefq")
		self.assertEqual(message.message, "!rb andref 72")
		self.assertEqual(message.user_command, "rb")
		self.assertEqual(message.arguments, ['andref', '72'])
	
	def test_normal_message(self):
		text = "@badge-info=;badges=moderator/1;color=#8A2BE2;display-name=kdancybot;emotes=;first-msg=0;flags=;id=475b82ec-63c9-40b6-b4dd-bf053f938ad5;mod=1;reply-parent-display-name=Andrefq;reply-parent-msg-body=!r;reply-parent-msg-id=71f5f911-9c35-44a9-a39b-8a50e95a36ff;reply-parent-user-id=156259639;reply-parent-user-login=andrefq;reply-thread-parent-msg-id=71f5f911-9c35-44a9-a39b-8a50e95a36ff;reply-thread-parent-user-login=andrefq;returning-chatter=0;room-id=156259639;subscriber=0;tmi-sent-ts=1688997860318;turbo=0;user-id=521795135;user-type=mod :kdancybot!kdancybot@kdancybot.tmi.twitch.tv PRIVMSG #andrefq :Hello!"
		message = Message(text)
		self.assertEqual(message.type, "PRIVMSG")
		self.assertEqual(message.user, "kdancybot")
		self.assertEqual(message.channel, "andrefq")
		self.assertEqual(message.message, "Hello!")
		self.assertEqual(message.user_command, None)
		self.assertEqual(message.arguments, None)
