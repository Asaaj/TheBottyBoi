#!/usr/bin/python3

import asyncio, discord, json, re, time, youtube_dl

import Screamer
ReloadableImports = [ Screamer ]

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
    'source_address': '0.0.0.0', # bind to ipv4 since ipv6 addresses cause issues sometimes,
	'retries': 'infinite'
}

ytdl_before_options = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

ffmpeg_options = {
    'options': '-vn'
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
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
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

class CmdFuncs:
	def __init__(self):
		self.__shouldStop = False
		self.__voiceClient = None

	async def Cleanup(self):
		if self.__voiceClient is not None:
			await self.__voiceClient.disconnect()
			self.__voiceClient = None

	async def stfu(self, fullMessage):
		self.__shouldStop = True
		await self.Cleanup()

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

	async def stream(self, client, fullMessage, url):
		if self.__voiceClient is not None and self.__voiceClient.is_playing():
			self.__voiceClient.stop()
		if self.__voiceClient is None:
			voiceChannel = self.__GetVoiceChannel(client, fullMessage)
			self.__voiceClient = await voiceChannel.connect()

		async with fullMessage.channel.typing():
			try:
				player = await YTDLSource.from_url(url, loop=client.loop, stream=True)
				self.__voiceClient.play(player, after=lambda e: print('Player error: %s' % e) if e else None)
				await Screamer.Scream(fullMessage.channel, "Now playing: **{}**".format(player.title))

			except Exception:
				await Screamer.Scream(fullMessage.channel, "I don't think that URL is supported. Try one for a Youtube video.")
				await self.Cleanup()

	async def volume(self, client, fullMessage, percent):
		if self.__voiceClient is None:
			await Screamer.Scream(fullMessage.channel, "I can't change the volume if I'm not playing anything.")
			return
		if int(percent) < 0 or int(percent) > 100:
			await Screamer.Scream(fullMessage.channel, "Volume has to be an integer between 0 and 100.")
			return 
		self.__voiceClient.source.volume = int(percent) / 100

	async def update(self, bot, fullMessage):
		await bot.UpdateAvatar()
		await Screamer.Scream(fullMessage.channel, "I have updated my avatar.")
