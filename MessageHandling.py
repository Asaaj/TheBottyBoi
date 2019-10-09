#!/usr/bin/python3

import importlib

from TheBottyBoi import TheBottyBoi
ReloadableImports = [ TheBottyBoi ]

class MessageSanitizer:
	def __init__(self, botId):
		self.__botId = botId
		self.__botMentions = [
			"<@{}>".format(botId),
			"<@!{}>".format(botId)
		]

	def StartsWithBotMention(self, content):
		return any([content.strip().startswith(mention) for mention in self.__botMentions])

	def RemoveBotMentionFromStart(self, content):
		whichMentions = [i for i, m in enumerate(self.__botMentions) if content.startswith(m)]
		return content[len(whichMentions) > 0 and len(self.__botMentions[whichMentions[0]]):].strip()

	def SanitizeContent(self, content):
		return self.RemoveBotMentionFromStart(content)

class MaybeDidntLoad:
	LoadIssue = None
	def GetLoadIssue(self):
		return self.LoadIssue

class CommandDispatcher(MaybeDidntLoad):
	def __init__(self, botId):
		self.__sanitizer = MessageSanitizer(botId)
		try:
			self.__maBoi = TheBottyBoi(botId)
		except Exception as e:
			self.LoadIssue = e

	def ShouldDispatchMessage(self, message):
		return self.__sanitizer.StartsWithBotMention(message.content) or self.__maBoi.IsThisMessageSpecial(message)

	def ShouldReloadConfiguration(self, message):
		return self.ShouldDispatchMessage(message) and self.__sanitizer.SanitizeContent(message.content) == "reload"

	def ShouldExit(self, message):
		return self.ShouldDispatchMessage(message) and self.__sanitizer.SanitizeContent(message.content) == "exit"

	def Dispatch(self, message):
		content = self.__sanitizer.SanitizeContent(message.content)
		self.__maBoi.DealWithIt(content, message)
