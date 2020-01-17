#!/usr/bin/python3

import inspect, json, re, shlex, unittest, urllib
from random import randrange

import CommandFunctions, CommandValidation, Screamer
ReloadableImports = [ CommandFunctions, CommandValidation, Screamer ]

botAvatarPath = "blotty.png"

class Handlers:
	def __init__(self, clientConnection, bot):
		self.__functions = CommandFunctions.CmdFuncs()
		self.__client = clientConnection
		self.__bot = bot

	async def Cleanup(self):
		await self.__functions.Cleanup()

	def __GetArgNameValueMap(self, commandDef, sanitizedContent):
		argNames = commandDef["args"]

		argString = sanitizedContent[len(commandDef["cmd"]):].strip()
		argValues = shlex.split(argString)
		argValues += [None] * (len(argNames) - len(argValues))

		return dict(zip(argNames, argValues))

	def __GetFormatted(self, fmt, nameValueMap):
		reply = fmt
		for name, value in nameValueMap.items():
			reply = reply.replace("{{{}}}".format(name), value)
		return reply

	async def DocReply(self, commandDef, sanitizedContent, fullMessage):
		filePath = "docreply/{}.txt".format(commandDef["cmd"])
		replies = [line.strip() for line in open(filePath, 'r') if line.strip()]
		text = replies[randrange(len(replies))]

		if "args" not in commandDef:
			await Screamer.Scream(fullMessage.channel, text)
			return

		argNameValueMap = self.__GetArgNameValueMap(commandDef, sanitizedContent)
		reply = self.__GetFormatted(commandDef["format"], argNameValueMap).replace("{{{}}}".format("value"), text)
		await Screamer.Scream(fullMessage.channel, reply)

	async def Reply(self, commandDef, sanitizedContent, fullMessage):
		if "args" not in commandDef:
			await Screamer.Scream(fullMessage.channel, commandDef["format"])
			return

		argNameValueMap = self.__GetArgNameValueMap(commandDef, sanitizedContent)
		reply = self.__GetFormatted(commandDef["format"], argNameValueMap)
		await Screamer.Scream(fullMessage.channel, reply)
	
	async def Function(self, commandDef, sanitizedContent, fullMessage):
		if "args" in commandDef:
			argNameValueMap = self.__GetArgNameValueMap(commandDef, sanitizedContent)
			arguments = [value for _, value in argNameValueMap.items() if value]
		else:
			arguments = []
		
		arguments.insert(0, fullMessage)
		if "requires_client" in commandDef and commandDef["requires_client"]:
			arguments.insert(0, self.__client)

		if "requires_bot" in commandDef and commandDef["requires_bot"]:
			arguments.insert(0, self.__bot)

		if "func" in commandDef:
			functionName = commandDef["func"]
		else:
			functionName = commandDef["cmd"].replace(" ", "")
		funcPtr = getattr(self.__functions, functionName)

		if funcPtr is not None:
			if inspect.iscoroutinefunction(funcPtr):
				await funcPtr(*arguments)
			else:
				funcPtr(*arguments)

		else:
			raise AttributeError("Function '{}' does not exist. Perhaps you forgot to reload?".format(functionName))

class TheBottyBoi:
	__commandFile = "command_map.json"
	__commandMap = None
	__handlers = None
	__handlerMap = None
	__client = None

	def __Log(self, message):
		print("TheBottyBoi: " + message)

	def __LogMessage(self, message):
		print("{0.guild}\n    {0.author} <{0.created_at}>: {0.content}".format(message))

	def __init__(self, botId, clientConnection):
		self.__botId = botId
		self.__LoadCommandFile()
		self.__RunUnitTests()
		
		self.__client = clientConnection

		self.__handlers = Handlers(clientConnection, self)
		self.__handlerMap = {
			"docreply": self.__handlers.DocReply,
			"function": self.__handlers.Function,
			"reply": self.__handlers.Reply
		}

	async def UpdateAvatar(self):
		with open(botAvatarPath, "rb") as f:
			await self.__client.user.edit(avatar=f.read())

	async def Cleanup(self):
		await self.__handlers.Cleanup()

	def __LoadCommandFile(self):
		with open(self.__commandFile) as f:
			loadedJson = json.load(f)
			self.__commandMap = loadedJson['commands']
		
		mapValidator = CommandValidation.CommandMapValidator(self.__commandMap)
		mapValidator.Validate()

	def __RunUnitTests(self):
		loader = unittest.TestLoader()
		suite = loader.discover("./Test", pattern="Test*.py")
		self.__Log("Running {} unit tests".format(suite.countTestCases()))
		result = unittest.TextTestRunner().run(suite) 
		if not result.wasSuccessful():
			problems = result.failures
			problems.extend(result.errors)
			self.__Log("{} unit tests failed".format(len(problems)))
			raise AssertionError("Unit tests failed! Ran {} with {} failures".format(result.testsRun, len(problems)))
		self.__Log("Unit tests all ran successfully")

	async def __CantHandleMessage(self, channel, sender):
		await Screamer.Scream(channel, "I'm sorry, {}, I'm afraid I can't do that.".format(sender.mention))

	def __FindInCommandMap(self, sanitizedContent):
		for commandDef in self.__commandMap:
			if sanitizedContent.startswith(commandDef["cmd"]):
				return commandDef
		return None

	def IsThisMessageSpecial(self, message):
		return False

	async def DealWithIt(self, sanitizedContent, fullMessage):
		self.__LogMessage(fullMessage)

		commandDef = self.__FindInCommandMap(sanitizedContent)
		if commandDef is None:
			if self.IsThisMessageSpecial(fullMessage):
				await Screamer.Scream(fullMessage.channel, "Can't handle special messages yet.")
			else:
				await self.__CantHandleMessage(fullMessage.channel, fullMessage.author)
		
		else:
			await self.__handlerMap[commandDef["type"]](commandDef, sanitizedContent, fullMessage)
