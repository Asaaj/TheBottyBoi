#!/usr/bin/python3

import asyncio, discord, json, os, re, time, traceback, youtube_dl

import Leaderboard, Logger, Screamer
ReloadableImports = [ Leaderboard, Logger, Screamer ]

youtube_dl.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0' # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
	def __init__(self, source, *, data, volume=0.2):
		super().__init__(source, volume)

		self.data = data

		self.title = data.get('title')
		self.url = data.get('url')

	@classmethod
	async def from_url(cls, url, *, loop=None, stream=False):
		loop = loop or asyncio.get_event_loop()
		data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

		if 'entries' in data:
			# take first item from a playlist
			data = data['entries'][0]

		filename = data['url'] if stream else ytdl.prepare_filename(data)
		Logger.Log("AUDIO: Playing from file '{}'".format(filename), Logger.OKBLUE)
		return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class CmdFuncs:
	def __init__(self):
		self.__shouldStop = False
		self.__voiceClient = None

	def __CleanYoutubeFiles(self):
		files = os.listdir("./")
		for f in files:
			if f.startswith("youtube"):
				os.remove(f)

	async def Cleanup(self, client):
		if self.__voiceClient is not None:
			await client.change_presence(activity=None)
			await self.__voiceClient.disconnect()
			self.__voiceClient = None
		self.__CleanYoutubeFiles()

	async def stfu(self, client, fullMessage):
		self.__shouldStop = True
		await self.Cleanup(client)

	async def help(self, fullMessage, command=None):
		with open("command_map.json") as f:
			allCommands = json.load(f)["commands"]

		if command is not None:
			await self.__OutputUsage(fullMessage.channel, command, allCommands)
		else:
			await self.__OutputFullUsage(fullMessage.channel, allCommands)

	async def __OutputUsage(self, channel, command, allCommands):
		commandItem = self.__GetCommandItem(command, allCommands)
		await Screamer.Scream(channel, "Usage: \n```{}```".format(self.__GetUsage(commandItem)))

	async def __OutputFullUsage(self, channel, allCommands):
		onlyVisibleCommands = [i for i in allCommands if "hidden" not in i or not i["hidden"]]

		output = "Here's everything I know how to do:\n```"
		for commandItem in onlyVisibleCommands:
			output += self.__GetUsage(commandItem) + "\n"
		await Screamer.Scream(channel, output + "```")

	def __GetUsage(self, commandItem):
		output = " > " + commandItem["cmd"]
		if "args" in commandItem:
			output += " " + " ".join(self.__PrintableArgs(commandItem["args"]))
		if "help" in commandItem:
			output += "\n    : " + commandItem["help"]
		return output + "\n"

	def __PrintableArgs(self, args):
		return ["<{}>".format(arg) if not re.match(R"\[.*\]", arg) else arg for arg in args]

	def __GetCommandItem(self, command, allCommands):
		return [item for item in allCommands if item["cmd"] == command][0]

	async def prod(self, fullMessage, user, num="1", wait="3"):
		maxSpam = 10
		message = "Hey {}, join us in voice.".format(user)
		if int(num) > maxSpam:
			num = str(maxSpam)
			await Screamer.Scream(fullMessage.channel, "That's too many times! I'll prod him {} times.".format(num))

		count = 0
		while count < int(num) and not self.__shouldStop:
			await Screamer.Scream(fullMessage.channel, message)
			time.sleep(float(wait))
			count += 1
		self.__shouldStop = False


	##############
	### Stream ###
	##############
	def __GetVoiceChannel(self, client, fullMessage):
		sender = fullMessage.author
		if not hasattr(sender, "voice"):
			return None

		if sender.voice is None:
			allChannels = list(client.get_all_channels())
			voiceChannels = [c for c in allChannels if isinstance(c, discord.VoiceChannel)]
			return max(voiceChannels, key=lambda c: len(c.members))
		else:
			return sender.voice.channel

	def __GetStreamFinished(self, client):
		def __StreamFinished(self, e=None):
			if e:
				Logger.Log("Player error: %s" % e, Logger.ERROR)
			else:
				try:
					asyncio.ensure_future(self.Cleanup(client))
				except Exception as e:
					Logger.Log(f"Exception when cleaning up player! {str(e)}", Logger.ERROR)
					Logger.Log(traceback.format_exc(), Logger.ERROR)
		return __StreamFinished

	async def play(self, client, fullMessage, url):
		if self.__voiceClient is not None and self.__voiceClient.is_playing():
			self.__voiceClient.stop()
		if self.__voiceClient is None:
			voiceChannel = self.__GetVoiceChannel(client, fullMessage)
			self.__voiceClient = await voiceChannel.connect()

		async with fullMessage.channel.typing():
			try:
				player = await YTDLSource.from_url(url, loop=client.loop, stream=False)
				self.__voiceClient.play(player, after=self.__GetStreamFinished(client))
				await Screamer.Scream(fullMessage.channel, "Now playing: **{}**".format(player.title))
				stream = discord.Game(player.title)
				await client.change_presence(activity=stream)

			except Exception as e:
				await Screamer.Scream(fullMessage.channel, "Hmm, something went wrong with playback. Invalid search or URL, maybe? Check the output for more information.")
				Logger.Log("EXCEPTION: " + str(e), Logger.ERROR)
				await self.Cleanup(client)

	async def volume(self, client, fullMessage, percent):
		if self.__voiceClient is None:
			await Screamer.Scream(fullMessage.channel, "I can't change the volume if I'm not playing anything.")
			return
		if int(percent) < 0 or int(percent) > 100:
			await Screamer.Scream(fullMessage.channel, "Volume has to be an integer between 0 and 100.")
			return 
		self.__voiceClient.source.volume = int(percent) / 100


	###################
	### Leaderboard ###
	###################
	__leaderboards = Leaderboard.LeaderboardCollection()
	async def leaderboard(self, bot, fullMessage):
		await self.__leaderboards.PrintMessageAuthorPoints(bot, fullMessage.channel)

	## Dev-only
	async def cache(self, bot, fullMessage):
		await self.__leaderboards.CacheChannel(bot, fullMessage.channel)

	######################
	### Drinking Games ###
	######################
	__drinkingGameChannel = "drinking-games"
	__rulesThatApplyToAll = "all"
	__categories = {
	##	"message prefix"  : "printed category output"
		"everyone drinks" : "Everyone drinks",
		"you drink"       : "You drink"
	}
	__uncategorizedPrefix = "Other"

	async def __GetDrinkingGameChannel(self, fullMessage):
		guild = fullMessage.guild
		if guild is None:
			Logger.Log("Message had no associated guild. Cannot get a drinking game channel", Logger.ERROR)
			return None

		channels = guild.text_channels
		channel = next((c for c in channels if c.name == self.__drinkingGameChannel), None)
		if channel is None:
			Logger.Log(f"Couldn't find #{self.__drinkingGameChannel}", Logger.ERROR)
			await Screamer.Scream(fullMessage.channel, f"Sorry, I couldn't find a channel called #{self.__drinkingGameChannel}.")
		else:
			Logger.Log(f"Found channel #{channel.name}", Logger.SUCCESS)

		return channel

	async def __GetDrinkingGameMap(self, fullMessage):
		gameChannel = await self.__GetDrinkingGameChannel(fullMessage)
		if gameChannel is None:
			return

		gameToRulesMap = {}
		# await Screamer.Scream(fullMessage.channel, "Compiling rules...")
		async with fullMessage.channel.typing():
			async for message in gameChannel.history():
				matches = re.search("^@([A-Za-z0-9]*) (.*)", message.content.strip())
				if matches is None or len(matches.groups()) != 2:
					continue

				Logger.Log(Logger.AsHeader("Game rule: ") + str(matches.groups()))
				game = matches.group(1).lower()
				rules = matches.group(2)  ## Not lower(), keep the capitalization
				if game not in gameToRulesMap:
					gameToRulesMap[game] = []
				gameToRulesMap[game].append(rules)

		if len(gameToRulesMap) == 0:
			Logger.Log("Drinking game channel had no games!", Logger.WARNING)
			await Screamer.Scream(fullMessage.channel, f"No games found in #{self.__drinkingGameChannel}")

		return gameToRulesMap

	async def drinkinggames(self, fullMessage):
		gameToRulesMap = await self.__GetDrinkingGameMap(fullMessage)
		output = "Here are the games:\n```"
		longestName = max([len(game) for game in gameToRulesMap])
		sortedGames = dict(sorted(gameToRulesMap.items()))
		for game, rules in [(g, r) for g, r in sortedGames.items() if g != self.__rulesThatApplyToAll]:
			additionalSpaces = " " * (longestName - len(game) + 1)
			numRules = len(rules)
			rulesLabel = "rule" if numRules == 1 else "rules"
			output += f"> {game.title()}{additionalSpaces}({len(rules)} {rulesLabel})\n"
		output += "```"

		await Screamer.Scream(fullMessage.channel, output)

	def __DivideIntoCategories(self, gamesToShow, gameToRulesMap):
		categoryToRulesMap = {}
		onlyGamesToShow = [(g, r) for g, r in gameToRulesMap.items() if g in gamesToShow]
		for game, rulesForGame in onlyGamesToShow:
			Logger.Log(f"Game '{game}': {rulesForGame}", Logger.OKBLUE)

			for rule in rulesForGame:
				foundPrefix = next((prefix for prefix in self.__categories if rule.startswith(prefix)), None)
				if foundPrefix is None:
					printablePrefix = self.__uncategorizedPrefix
				else:
					printablePrefix = self.__categories[foundPrefix]
					rule = rule[len(foundPrefix):]  ## Trim since it fits in a category

				if printablePrefix not in categoryToRulesMap:
					categoryToRulesMap[printablePrefix] = []
				categoryToRulesMap[printablePrefix].append(rule)

		return categoryToRulesMap

	async def __OutputRulesForOneGame(self, fullMessage, game):
		gameToRulesMap = await self.__GetDrinkingGameMap(fullMessage)
		game = game.lower()
		if game not in gameToRulesMap:
			await Screamer.Scream(fullMessage.channel, f"Sorry, '{game.title()}' is not a valid game.")
			await self.drinkinggames(fullMessage)
			return

		rules = self.__DivideIntoCategories([self.__rulesThatApplyToAll, game], gameToRulesMap)

		output = f"Rules for game '{game.title()}':\n```"
		for category, rules in rules.items():
			output += f"{category}:\n"
			for rule in rules:
				output += f"  - {rule}\n"
			output += "\n"
		
		output += "```"
		await Screamer.Scream(fullMessage.channel, output)

	async def rules(self, fullMessage, game=None):
		if game is not None:
			await self.__OutputRulesForOneGame(fullMessage, game)
		else:
			## TODO: This calls the rebuild twice. It really shouldn't
			gameToRulesMap = await self.__GetDrinkingGameMap(fullMessage)
			for singleGame in [g for g in gameToRulesMap if g != self.__rulesThatApplyToAll]:
				await self.__OutputRulesForOneGame(fullMessage, singleGame)
