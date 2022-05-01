import datetime, discord, os, pathlib

import Logger, Screamer
ReloadableImports = [ Logger, Screamer ]

try:
	import dill as pickle
except ModuleNotFoundError:
	import pickle
	Logger.Log("Couldn't find pickle alternative; using the normal one", Logger.WARNING)

class SerializableMessage:
	@staticmethod
	async def create(original: discord.Message):
		reactions = [await SerializableReaction.create(r) for r in original.reactions]
		return SerializableMessage(original, reactions)

	def __init__(self, original: discord.Message, reactions: list):
		self.id = original.id
		self.author = SerializableAuthor(original.author)
		self.content = original.content
		self.reactions = reactions
		self.created_at = original.created_at
		self.edited_at = original.edited_at
		self.jump_url = original.jump_url

class SerializableAuthor:
	def __init__(self, original: discord.User):
		self.id = original.id
		self.name = original.name

	def __str__(self):
		return self.name # TODO: Should keep descriminator

class SerializableReaction:
	@staticmethod
	async def create(original: discord.Reaction):
		userIds = [u.id for u in await original.users().flatten()]
		return SerializableReaction(original, userIds)

	def __init__(self, original: discord.Reaction, userIds: list):
		self.emoji = SerializableEmoji(original.emoji)
		self.count = original.count
		self.custom_emoji = original.custom_emoji
		self.userIds = userIds

class SerializableEmoji:
	def __init__(self, original):
		if type(original) == str:
			self.name = original
			self.id = None
		elif type(original) == discord.Emoji:
			self.name = original.name
			self.id = original.id
		elif type(original) == discord.PartialEmoji:
			Logger.Log(f"Partial emoji: {original}", Logger.WARNING)
			self.name = original.name if original.name is not None else ""
			self.id = original.id if original.id is not None else 0
		else:
			Logger.Log(f"Failed to parse emoji {original}", Logger.ERROR)

		# self.url = original.url # TODO

class ChannelCacher:
	## TODO: Need to work on synchronization. Not atomic
	__updatingCache = False

	async def Update(self, channel: discord.TextChannel, force_rebuild=False, after: datetime.datetime=None) -> None:
		if self.__updatingCache:
			await Screamer.Scream(channel, "Sorry, I'm already refreshing a cache! You'll have to wait a bit.")
			return
		
		try:
			self.__updatingCache = True
			cacheFile = self.__CreateCacheDirectories(channel)

			if not cacheFile.exists() or force_rebuild:
				await self.__CreateNewCacheFile(channel, cacheFile, after)
			else:
				await self.__UpdateCacheFile(channel, cacheFile, after)
		finally:
			self.__updatingCache = False

	def IterateCache(self, channel: discord.TextChannel, after: datetime.datetime):
		cacheFile = self.__GetCacheFilePath(channel)
		with open(cacheFile, "rb") as f:
			unpickler = pickle.Unpickler(f)
			while True:
				try:
					message = unpickler.load()
					if message.created_at >= after:
						yield message
				except EOFError:
					break
				except Exception as e:
					Logger.Log("Error during cache iteration!", Logger.ERROR)
					Logger.Log(f"{e}")


	def __GetCacheFilePath(self, channel) -> pathlib.Path:
		cachesPrefix = f"caches/discordpy_{discord.__version__}"
		channelCacheName = str(channel.id)
		
		channelCacheName = str(channel.id)
		if hasattr(channel, "guild"):
			guildPath = str(channel.guild.id)
		else:
			guildPath = channelCacheName

		cacheLocation = pathlib.Path(f"{cachesPrefix}/{guildPath}")
		return pathlib.Path(cacheLocation / channelCacheName)

	def __GetChannelReadableName(self, channel) -> str:
		if hasattr(channel, "guild"):
			return channel.name
		else:
			return f"<{channel.recipient.name}>"

	def __CreateCacheDirectories(self, channel: discord.TextChannel) -> pathlib.Path:
		cacheFile = self.__GetCacheFilePath(channel)
		cacheLocation = cacheFile.parent

		Logger.Log(f"Building cache for channel #{self.__GetChannelReadableName(channel)} ({cacheFile})", Logger.HEADER)
		cacheLocation.mkdir(parents=True, exist_ok=True)

		return cacheFile

	async def __CreateNewCacheFile(self, channel: discord.TextChannel, cacheFile: pathlib.Path, after: datetime.datetime) -> None:
		Logger.Log("Creating a new cache file...", Logger.OKBLUE)
		numMessages = await self.__SaveChannelMessages(channel, cacheFile, after=after)
		Logger.Log(f"Created cache file of {numMessages} messages", Logger.SUCCESS)

	async def __UpdateCacheFile(self, channel: discord.TextChannel, cacheFile: pathlib.Path, after: datetime.datetime) -> None:
		Logger.Log("Updating cache file...", Logger.OKBLUE)

		try:
			tagFile = self.__ToSavedTag(cacheFile)
			if not pathlib.Path(tagFile).exists():
				Logger.Log("Cache does not have a last-saved tag! I think I have to recreate this one...", Logger.ERROR)
				raise IOError("Missing last-saved tag file")
				
			with open(tagFile, "r") as f:
				last_saved = datetime.datetime.strptime(f.read(), self.__MessageTimeFormat())

			if after is not None and last_saved < after:
				Logger.Log(f"Last cache message as {last_saved}, but it should have been after {after}", Logger.WARNING)

			numMessages = await self.__SaveChannelMessages(channel, cacheFile, after=last_saved, append=True) # TODO: 100'000
			Logger.Log(f"Updated cache with {numMessages} messages", Logger.SUCCESS)

		except Exception as e:
			Logger.Log(f"Exception during cache update! {str(e)}", Logger.ERROR)
			Logger.Log("Refreshing cache.", Logger.WARNING)
			await self.__CreateNewCacheFile(channel, cacheFile, after)

		#numLoaded = 0
		#for serialized in self.IterateCache(channel):
		#	numLoaded += 1
		#Logger.Log(f"Loaded {numLoaded} messages", Logger.SUCCESS)

	async def __SaveMessage(self, pickler, message: discord.Message, cacheFile: pathlib.Path) -> None:
		pickler.dump(await SerializableMessage.create(message))
		self.__TagLastMessageSaved(message, cacheFile)

	async def __SaveChannelMessages(self, channel: discord.TextChannel, cacheFile: pathlib.Path, after: datetime.datetime, append=False) -> int:
		writeMode = "ab+" if append else "wb+"
		with open(cacheFile, writeMode) as cache:
			pickler = pickle.Pickler(cache)
			numMessages = 0
			async for message in channel.history(oldest_first=True, limit=100000, after=after):
				numMessages += 1
				fileSize = os.path.getsize(cacheFile)
				if fileSize > 2.147 * (10**9): # 2 GB
					Logger.Log("Cache file is over 2 GiB! Aborting cache", Logger.ERROR)
					raise IOError("Cache file too big")
				await self.__SaveMessage(pickler, message, cacheFile)
			return numMessages

	def __MessageTimeFormat(self) -> str:
		return "%y-%m-%d_%H:%M:%S.%f"

	def __ToSavedTag(self, cacheFile: pathlib.Path) -> pathlib.Path:
		return cacheFile.parent / (cacheFile.name + ".last_saved")

	def __TagLastMessageSaved(self, message: discord.Message,  cacheFile: pathlib.Path) -> None:
		with open(self.__ToSavedTag(cacheFile), "w") as f:
			f.write(message.created_at.strftime(self.__MessageTimeFormat()))
