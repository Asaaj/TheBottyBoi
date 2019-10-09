#!/usr/bin/python3

import discord, os
from types import ModuleType

try:
	from importlib import reload  # Python 3.4+
except ImportError:
	from imp import reload

import MessageHandling, Broadcaster
ReloadableImports = [ MessageHandling, Broadcaster ]

def ReloadReloadableModule(module, alreadyReloaded):
	print("Reloading {}".format(module.__name__))
	reload(module)
	alreadyReloaded.add(module)
	if not hasattr(module, "ReloadableImports"):
		return
	for dependency in module.ReloadableImports:
		ReloadReloadableModule(dependency, alreadyReloaded)

class API:
	ClientId = os.environ.get("BOTTY_ID")
	BotToken = os.environ.get("BOTTY_TOKEN")

class Chauffeur(discord.Client):
	__lastReloadSuccessful = True

	async def __HandleReload(self, channel):
		reloaded = self.__ReloadModules()
		self.__LoadHandlers()
		handlerLoadIssues = self.__GetHandlerLoadIssues()
		if any(handlerLoadIssues):
			await Broadcaster.Broadcast(channel, "There was a problem loading the message handlers. I will only respond to the 'reload' and 'exit' commands until the errors are resolved. See the log for more details.")
			print("ERROR: Problems with reload!")
			for problem in [p for p in handlerLoadIssues if p]:
				print(str(problem))
			self.__lastReloadSuccessful = False
			return

		self.__lastReloadSuccessful = True
		await Broadcaster.Broadcast(channel, "Successfully reloaded ({} unique modules reloaded)".format(len(reloaded)))

	def __ReloadModules(self):
		reloaded = set()
		for mod in ReloadableImports:
			ReloadReloadableModule(mod, reloaded)
		return reloaded

	def __LoadHandlers(self):
		self.__dispatcher = MessageHandling.CommandDispatcher(API.ClientId)

	def __GetHandlerLoadIssues(self):
		return [self.__dispatcher.GetLoadIssue()]

	async def on_ready(self):
		print("Successfully logged in as '{}'".format(self.user))
		print("Channels: ", [c.name for c in list(self.get_all_channels())])
		self.__LoadHandlers()

	async def on_message(self, message):
		if self.__dispatcher.ShouldReloadConfiguration(message):
			self.__HandleReload(message.channel)
		elif self.__dispatcher.ShouldExit(message):
			await self.close()
		elif self.__dispatcher.ShouldDispatchMessage(message):
			if self.__lastReloadSuccessful:
				self.__dispatcher.Dispatch(message)
			else:
				await Broadcaster.Broadcast(message.channel, "Sorry, I can't handle commands until you correct the last reload errors.")

if __name__ == '__main__':
	print("Using discordpy version " + discord.__version__)

	if all([API.ClientId, API.BotToken]):
		chauffeur = Chauffeur()
		chauffeur.run(API.BotToken)
	else:
		print("This app requires the environment variables BOTTY_ID and BOTTY_TOKEN.\n"
		      "Please export those tokens with the corresponding information for your bot.\n"
		      "Exiting.")
