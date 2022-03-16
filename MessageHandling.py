#!/usr/bin/python3

import datetime, importlib, os, traceback

import Logger, MessageSanitizer, Screamer, TheBottyBoi
ReloadableImports = [ Logger, MessageSanitizer, Screamer, TheBottyBoi ]

class Environment:
	AdminIdFile = os.getenv("BOTTY_ADMIN_ID_FILE") ## File containing Discord IDs of admins who can reload, exit, etc.

class MaybeDidntLoad:
	LoadIssue = None
	def GetLoadIssue(self):
		return self.LoadIssue

class CommandDispatcher(MaybeDidntLoad):
	def __init__(self, botId, clientConnection):
		self.__LoadAdminIds()
		self.__sanitizer = MessageSanitizer.MessageSanitizer(botId)
		try:
			self.__maBoi = TheBottyBoi.TheBottyBoi(botId, clientConnection, self.__adminIds)
		except Exception as e:
			self.__maBoi = None
			self.LoadIssue = e

	def __LoadAdminIds(self):
		self.__adminIds = []
		if Environment.AdminIdFile is None:
			Logger.Log("BOTTY_ADMIN_ID_FILE environment variable is apparently not set!", Logger.ERROR)
			return
		if not os.path.exists(Environment.AdminIdFile):
			Logger.Log("File specified by the BOTTY_ADMIN_ID_FILE environment variable does not exist!", Logger.ERROR)
			return
		with open(Environment.AdminIdFile) as f:
			try:
				self.__adminIds = [int(stripped_line) for line in f.readlines() if (stripped_line := line.strip())]
				Logger.Log(f"Loaded admin IDs from {Environment.AdminIdFile}: {self.__adminIds}", Logger.SUCCESS)
			except:
				Logger.Log("File specified by the BOTTY_ADMIN_ID_FILE environment variable couldn't be parsed! Make sure it's just integers on their own lines.", Logger.ERROR)

	async def Cleanup(self):
		if self.__maBoi is not None:
			await self.__maBoi.Cleanup()

	async def AlertAdmins(self, msg):
		for admin in self.__adminIds:
			await self.__maBoi.SendDm(admin, msg)

	def ShouldReloadConfiguration(self, message):
		return self.ShouldDispatchMessage(message) and \
			self.__sanitizer.RemoveBotMentionFromStart(message.content) == "reload" and \
			message.author.id in self.__adminIds

	def ShouldExit(self, message):
		return self.ShouldDispatchMessage(message) and \
			self.__sanitizer.RemoveBotMentionFromStart(message.content) == "exit" and \
			message.author.id in self.__adminIds

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
