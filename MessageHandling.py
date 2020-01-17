#!/usr/bin/python3

import importlib, traceback

import MessageSanitizer, Screamer, TheBottyBoi
ReloadableImports = [ MessageSanitizer, Screamer, TheBottyBoi ]

## The only one who can send "reload" commands
theMaster = "184456961255800832"

class MaybeDidntLoad:
	LoadIssue = None
	def GetLoadIssue(self):
		return self.LoadIssue

class CommandDispatcher(MaybeDidntLoad):
	def __init__(self, botId, clientConnection):
		self.__sanitizer = MessageSanitizer.MessageSanitizer(botId)
		try:
			self.__maBoi = TheBottyBoi.TheBottyBoi(botId, clientConnection)
		except Exception as e:
			self.__maBoi = None
			self.LoadIssue = e

	async def Cleanup(self):
		if self.__maBoi is not None:
			await self.__maBoi.Cleanup()

	def ShouldReloadConfiguration(self, message):
		return self.ShouldDispatchMessage(message) and self.__sanitizer.RemoveBotMentionFromStart(message.content) == "reload" and str(message.author.id) == theMaster

	def ShouldDispatchMessage(self, message):
		if self.__maBoi is None:
			return self.__sanitizer.StartsWithBotMention(message.content)
		return self.__sanitizer.StartsWithBotMention(message.content) or self.__maBoi.IsThisMessageSpecial(message)

	async def Dispatch(self, message):
		content = self.__sanitizer.SanitizeContent(message.content)
		try:
			await self.__maBoi.DealWithIt(content, message)
		except Exception as e:
			await Screamer.Scream(message.channel, "Uh oh! An exception occurred during that one. Here's the output:\n    `{}`".format(str(e)))
			await Screamer.Scream(message.channel, "```" + traceback.format_exc() + "```")
