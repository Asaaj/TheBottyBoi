#!/usr/bin/python3

import asyncio, datetime, discord, os
from types import ModuleType

try:
    from importlib import reload  # Python 3.4+
except ImportError:
    from imp import reload

import Logger, MessageHandling, Screamer
ReloadableImports = [ Logger, MessageHandling, Screamer ]

def ReloadReloadableModule(module, alreadyReloaded):
	Logger.Log("Reloading {}".format(module.__name__), Logger.HEADER)
	reload(module)
	alreadyReloaded.add(module)
	if not hasattr(module, "ReloadableImports"):
		return
	for dependency in module.ReloadableImports:
		ReloadReloadableModule(dependency, alreadyReloaded)

class API:
	ClientId = os.getenv("BOTTY_ID")
	BotToken = os.getenv("BOTTY_TOKEN")

class Chauffeur(discord.Client):
	__lastReloadSuccessful = True

	async def __HandleReload(self, channel):
		failedThisTime = False
		try:
			await self.__dispatcher.Cleanup()
			reloaded = self.__ReloadModules()
			self.__LoadHandlers()
			handlerLoadIssues = self.__GetHandlerLoadIssues()
			if any(handlerLoadIssues):
				await Screamer.Scream(channel, "There was a problem loading the message handlers. I will only respond to the 'reload' command until the errors are resolved. See the log for more details.")
				Logger.Log("Problems with reload!", Logger.FAIL)
				for problem in [p for p in handlerLoadIssues if p]:
					Logger.Log(str(problem), Logger.WARNING)
				self.__lastReloadSuccessful = False
				failedThisTime = True

		except Exception as e:
			await Screamer.Scream(channel, "An exception was thrown while reloading. I will only respond to to the 'reload' command until the errors are resolved. See the log for more details.")
			Logger.Log("EXCEPTION: " + str(e), Logger.FAIL)
			self.__lastReloadSuccessful = False
			failedThisTime = True

		if failedThisTime:
			Logger.Log("Setting status to 'busy'", Logger.WARNING)
			activity = discord.CustomActivity("Problems reloading")
			await self.change_presence(status=discord.Status.do_not_disturb, activity=activity)
			return

		self.__lastReloadSuccessful = True
		await self.change_presence(status=discord.Status.online)
		await Screamer.Scream(channel, "Successfully reloaded ({} unique modules reloaded)".format(len(reloaded)))

	def __ReloadModules(self):
		reloaded = set()
		for mod in ReloadableImports:
			ReloadReloadableModule(mod, reloaded)
		return reloaded

	def __LoadHandlers(self):
		self.__dispatcher = MessageHandling.CommandDispatcher(API.ClientId, self)

	def __GetHandlerLoadIssues(self):
		return [self.__dispatcher.GetLoadIssue()]

	async def __SendDm(self, userId, message):
		userObject = self.get_user(int(userId))
		if userObject is None:
			Logger.Log(f"Failed to send DM to <@{userId}>", Logger.FAIL)
			return
		dmChannel = await userObject.create_dm()
		Logger.Log(f"DM <@{userId}> <{datetime.datetime.now()}>: {message}")
		await dmChannel.send(message)

	## The only one who can send "reload" and "exit" commands
	def GetMasterId(self):
		return "184456961255800832"

	async def on_ready(self):
		Logger.Log("Successfully logged in as '{}'".format(self.user), Logger.SUCCESS)
		Logger.Log("Time: " + str(datetime.datetime.now()))
		Logger.Log("Channels: " + str([c.name for c in list(self.get_all_channels())]))
		self.__LoadHandlers()

		await self.__SendDm(self.GetMasterId(), f"Logged in at {datetime.datetime.now()}")

	async def on_message(self, message):
		try:
			if self.__dispatcher.ShouldReloadConfiguration(message):
				await self.__HandleReload(message.channel)
			elif self.__dispatcher.ShouldExit(message):
				await Screamer.Scream(message.channel, "Goodbye! <3")
				await self.close()
			elif self.__dispatcher.ShouldDispatchMessage(message):
				if self.__lastReloadSuccessful:
					await self.__dispatcher.Dispatch(message)
				else:
					await Screamer.Scream(message.channel, "Sorry, I can't handle commands until you correct the last reload errors.")
		except Exception as e:
			Logger.Log("EXCEPTION: " + str(e), Logger.FAIL)
			await Screamer.Scream(message.channel, "Whoops, I hit some unforeseen exception. Check the output for more information.")
		
if __name__ == '__main__':
	print("\n\n")
	Logger.Log(f"Using discordpy version {discord.__version__}", Logger.HEADER)
	if all([API.ClientId, API.BotToken]):
		chauffeur = Chauffeur()
		chauffeur.run(API.BotToken)
	else:
		print("This app requires the environment variables BOTTY_ID and BOTTY_TOKEN.\n"
		      "Please export those tokens with the corresponding information for your bot.\n"
		      "Exiting.")

