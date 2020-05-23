#!/usr/bin/python3

import json, unittest, urllib

import CommandHandlers, CommandValidation, Logger, Screamer, UnitTests
ReloadableImports = [ CommandHandlers, CommandValidation, Logger, Screamer, UnitTests ]

botAvatarPath = "blotty.png"

class TheBottyBoi:
	__commandFile = "command_map.json"
	__commandMap = None
	__handlers = None
	__client = None

	def __Log(self, message):
		Logger.Log(Logger.AsHeader("TheBottyBoi") + ": " + message)

	def __LogMessage(self, message):
		guildPrefix = ""
		if message.guild is not None:
			guildPrefix = Logger.AsHeader(f"{message.guild}") + ": "
		Logger.Log(guildPrefix + Logger.GetFormattedMessage(message))

	def __init__(self, botId, clientConnection):
		self.__botId = botId
		self.__LoadCommandFile()
		self.__RunUnitTests()
		
		self.__client = clientConnection

		self.__handlers = {
			"docreply": CommandHandlers.DocReplyHandler(),
			"function": CommandHandlers.FunctionHandler(clientConnection, self),
			"reply": CommandHandlers.ReplyHandler(),
			"special": CommandHandlers.SpecialHandler()
		}

	def GetRawClient(self):
		return self.__client

	async def UpdateAvatar(self):
		with open(botAvatarPath, "rb") as f:
			await self.__client.user.edit(avatar=f.read())

	async def Cleanup(self):
		for handler in self.__handlers.values():
			await handler.Cleanup()

	def __LoadCommandFile(self):
		with open(self.__commandFile) as f:
			loadedJson = json.load(f)
			self.__commandMap = loadedJson['commands']
		
		mapValidator = CommandValidation.CommandMapValidator(self.__commandMap)
		mapValidator.Validate()

	def __RunUnitTests(self):
		loader = unittest.TestLoader()
		suite = loader.discover(".", pattern="Test*.py")
		self.__Log("Running {} unit tests".format(suite.countTestCases()))
		result = unittest.TextTestRunner().run(suite) 
		if not result.wasSuccessful():
			problems = result.failures
			problems.extend(result.errors)
			self.__Log("{} unit tests failed".format(len(problems)))
			raise AssertionError("Unit tests failed! Ran {} with {} failures".format(result.testsRun, len(problems)))
		self.__Log("Unit tests all ran successfully")

	def IsThisMessageSpecial(self, message):
		return self.__handlers["special"].ShouldHandle(message)

	async def DealWithIt(self, sanitizedContent, fullMessage):
		self.__LogMessage(fullMessage)

		commandDef = self.__FindInCommandMap(sanitizedContent)
		if commandDef is None:
			if self.IsThisMessageSpecial(fullMessage):
				await self.__handlers["special"].Handle(commandDef, sanitizedContent, fullMessage)
			else:
				await self.__CantHandleMessage(fullMessage.channel, fullMessage.author)
		
		else:
			await self.__handlers[commandDef["type"]].Handle(commandDef, sanitizedContent, fullMessage)

	async def __CantHandleMessage(self, channel, sender):
		await Screamer.Scream(channel, "I'm sorry, {}, I'm afraid I can't do that.".format(sender.mention))

	def __FindInCommandMap(self, sanitizedContent):
		for commandDef in self.__commandMap:
			if sanitizedContent.startswith(commandDef["cmd"]):
				return commandDef
		return None
