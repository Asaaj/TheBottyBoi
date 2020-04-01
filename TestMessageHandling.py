import sys, unittest
from io import StringIO

import MessageHandling, MessageSanitizer, TestStructures

class TestMessageSanitizer(unittest.TestCase):
	def setUp(self):
		self.__old_stdout = sys.stdout
		sys.stdout = self.__stdout = StringIO()

	def tearDown(self):
		sys.stdout = self.__old_stdout

	def test_StartsWithBotName(self):
		botId = 1001
		message = "<@{}> this is a message".format(botId)
		sanitizer = MessageSanitizer.MessageSanitizer(botId)

		self.assertTrue(sanitizer.StartsWithBotMention(message))

	def test_StartsWithBotNickname(self):
		botId = 1001
		message = "<@!{}> this is a message".format(botId)
		sanitizer = MessageSanitizer.MessageSanitizer(botId)

		self.assertTrue(sanitizer.StartsWithBotMention(message))

	def test_ContainsBotMention(self):
		botId = 1001
		message = "this is a message, <@{}>".format(botId)
		sanitizer = MessageSanitizer.MessageSanitizer(botId)

		self.assertFalse(sanitizer.StartsWithBotMention(message))

	def test_DoesntContainBotMention(self):
		botId = 1001
		message = "<@2002> this isnt for the bot"
		sanitizer = MessageSanitizer.MessageSanitizer(botId)

		self.assertFalse(sanitizer.StartsWithBotMention(message))

	def test_RemoveBotMention(self):
		botId = 1001
		content = "here's a message"
		message = "<@!{}> {}".format(botId, content)
		sanitizer = MessageSanitizer.MessageSanitizer(botId)

		sanitized = sanitizer.RemoveBotMentionFromStart(message)

		self.assertEqual(sanitized, content)

	def test_NothingToRemove(self):
		botId = 1001
		content = "here's a message"
		message = "{} <@{}>".format(content, botId)
		sanitizer = MessageSanitizer.MessageSanitizer(botId)

		sanitized = sanitizer.RemoveBotMentionFromStart(message)

		self.assertEqual(sanitized, message)

if __name__ == "__main__":
	unittest.main()