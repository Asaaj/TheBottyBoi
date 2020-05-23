#!/usr/bin/python3

import asyncio, datetime, discord, os
from types import ModuleType

try:
    from importlib import reload  # Python 3.4+
except ImportError:
    from imp import reload

import MessageHandling, Screamer
ReloadableImports = [ MessageHandling, Screamer ]

def ReloadReloadableModule(module, alreadyReloaded):
	print("Reloading {}".format(module.__name__))
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
		try:
			await self.__dispatcher.Cleanup()
			reloaded = self.__ReloadModules()
			self.__LoadHandlers()
			handlerLoadIssues = self.__GetHandlerLoadIssues()
			if any(handlerLoadIssues):
				await Screamer.Scream(channel, "There was a problem loading the message handlers. I will only respond to the 'reload' command until the errors are resolved. See the log for more details.")
				print("ERROR: Problems with reload!")
				for problem in [p for p in handlerLoadIssues if p]:
					print(str(problem))
				self.__lastReloadSuccessful = False
				return
		except Exception as e:
			await Screamer.Scream(channel, "An exception was thrown while reloading. I will only respond to to the 'reload' command until the errors are resolved. See the log for more details.")
			print("EXCEPTION: " + str(e))
			self.__lastReloadSuccessful = False
			return

		self.__lastReloadSuccessful = True
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
			print(f"!! Failed to send DM to <@{userId}>")
			return
		dmChannel = await userObject.create_dm()
		print(f"DM <@{userId}> <{datetime.datetime.now()}>: {message}")
		await dmChannel.send(message)

	## The only one who can send "reload" and "exit" commands
	def GetMasterId(self):
		return "184456961255800832"

	async def on_ready(self):
		print("Successfully logged in as '{}'".format(self.user))
		print("Time: " + str(datetime.datetime.now()))
		print("Channels: ", [c.name for c in list(self.get_all_channels())])
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
			print("EXCEPTION: " + str(e))
			await Screamer.Scream(message.channel, "Whoops, I hit some unforeseen exception. Check the output for more information.")
		
if __name__ == '__main__':
	print(f"\n\n\n<{datetime.datetime.now()}> Using discordpy version {discord.__version__}")
	if all([API.ClientId, API.BotToken]):
		chauffeur = Chauffeur()
		chauffeur.run(API.BotToken)
	else:
		print("This app requires the environment variables BOTTY_ID and BOTTY_TOKEN.\n"
		      "Please export those tokens with the corresponding information for your bot.\n"
		      "Exiting.")

