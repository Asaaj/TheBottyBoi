import inspect, re, shlex
from random import randrange

import CommandFunctions, Screamer
ReloadableImports = [ CommandFunctions, Screamer ]

class CommandHandler:
	@staticmethod
	def GetFormatted(fmt, nameValueMap):
		reply = fmt
		for name, value in nameValueMap.items():
			reply = reply.replace("{{{}}}".format(name), value)
		return reply

	@staticmethod
	def GetArgNameValueMap(commandDef, sanitizedContent):
		argNames = commandDef["args"]

		argString = sanitizedContent[len(commandDef["cmd"]):].strip()
		argValues = shlex.split(argString)
		argValues += [None] * (len(argNames) - len(argValues))

		return dict(zip(argNames, argValues))

	async def Cleanup(self):
		pass

class DocReplyHandler(CommandHandler):
	async def Handle(self, commandDef, sanitizedContent, fullMessage):
		filePath = "docreply/{}.txt".format(commandDef["cmd"])
		replies = [line.strip() for line in open(filePath, 'r') if line.strip()]
		text = replies[randrange(len(replies))]

		if "args" not in commandDef:
			await Screamer.Scream(fullMessage.channel, text)
			return

		argNameValueMap = CommandHandler.GetArgNameValueMap(commandDef, sanitizedContent)
		if "user" in argNameValueMap and argNameValueMap["user"] == "me":
			argNameValueMap["user"] = fullMessage.author.mention
		reply = CommandHandler.GetFormatted(commandDef["format"], argNameValueMap).replace("{{{}}}".format("value"), text)
		await Screamer.Scream(fullMessage.channel, reply)

class ReplyHandler(CommandHandler):
	async def Handle(self, commandDef, sanitizedContent, fullMessage):
		if "args" not in commandDef:
			await Screamer.Scream(fullMessage.channel, commandDef["format"])
			return

		argNameValueMap = CommandHandler.GetArgNameValueMap(commandDef, sanitizedContent)
		reply = CommandHandler.GetFormatted(commandDef["format"], argNameValueMap)
		await Screamer.Scream(fullMessage.channel, reply)

class FunctionHandler(CommandHandler):
	def __init__(self, clientConnection, bot):
		self.__functions = CommandFunctions.CmdFuncs()
		self.__client = clientConnection
		self.__bot = bot

	async def Cleanup(self):
		await self.__functions.Cleanup(self.__client)

	async def Handle(self, commandDef, sanitizedContent, fullMessage):
		if "args" in commandDef:
			argNameValueMap = CommandHandler.GetArgNameValueMap(commandDef, sanitizedContent)
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

class SpecialHandler(CommandHandler):
	def __init__(self):
		self.__specialMessages = {
			R"(?i)yow pachow[.!]?": SpecialHandler.__YowPachow,
			"(?i)(fuck no|never)": SpecialHandler.__FuckNo,
			"(?i)(cuz|because|because I said so)": SpecialHandler.__Oh,
			"(?i)(you'?re?|ur) cute": SpecialHandler.__Cute
		}

	def ShouldHandle(self, fullMessage):
		for regex in self.__specialMessages.keys():
			if re.fullmatch(regex, fullMessage.content):
				return True

		return False

	async def Handle(self, commandDef, sanitizedContent, fullMessage):
		response = None
		for regex, handler in self.__specialMessages.items():
			if re.fullmatch(regex, fullMessage.content.strip()):
				response = handler(self, fullMessage)
		if response is not None:
			await Screamer.Scream(fullMessage.channel, response)

	def __YowPachow(self, fullMessage):
		return "fie fie may!"

	def __FuckNo(self, fullMessage):
		return "Why not? :("

	def __Oh(self, fullMessage):
		return "oh."

	def __Cute(self, fullMessage):
		return "uwu"
