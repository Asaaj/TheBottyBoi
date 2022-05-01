#!/usr/bin/python3
import asyncio, datetime, discord, os, pathlib, random
from typing import TypeVar, Generic

import ChannelCacher, Logger, Screamer
ReloadableImports = [ ChannelCacher, Logger, Screamer ]

class SelfAndTotalPoints:
	def __init__(self):
		self.Self = 0
		self.Total = 0

	def __str__(self):
		selfPointsString = ""
		if self.Self != 0:
			selfPointsString = f" ({self.Self} self votes)"
		return f"{self.Total} points{selfPointsString}"

	def __add__(self, other):
		newPoints = SelfAndTotalPoints()
		newPoints.Self = self.Self + other.Self
		newPoints.Total = self.Total + other.Total
		return newPoints

	## Don't really care about ordering by Self. Just use Total
	def __lt__(self, other):
		return self.Total < other.Total

	def __le__(self, other):
		return self.Total <= other.Total

	def __gt__(self, other):
		return self.Total > other.Total

	def __ge__(self, other):
		return self.Total >= other.Total

	def __eq__(self, other):
		return self.Total == other.Total

	def __ne__(self, other):
		return self.Total != other.Total

T = TypeVar('T')
class PointCounter(Generic[T]):
	def __init__(self, emojiName: str, userIdToPoints={}):
		self.__emojiName = emojiName
		self.UserIdToPoints = userIdToPoints.copy()

	## Merges two PointCounters, and adds the values of User IDs that are in both.
	## Requires an addition operator for T, the value type of UserIdToPoints.
	def __add__(self, other):
		thisDict = self.UserIdToPoints
		otherDict = other.UserIdToPoints
		return PointCounter(self.__emojiName, dict(list(thisDict.items()) + list(otherDict.items()) +
			[(userId, thisDict[userId] + otherDict[userId]) for userId in set(thisDict) & set(otherDict)]))

	def __str__(self):
		return str([(str(k), str(s)) for k, s in self.UserIdToPoints.items()])

	async def Count(self, message: discord.Message) -> None:
		self.__InitMessageAuthor(message)
		reaction = await self.__GetReactionFromMessage(message)
		if reaction is not None:
			self.ReactionUserIds = await self.__GetReactionUserIds(reaction)
			self.UserIdToPoints[message.author.id] += await self.GetCountsFrom(message, reaction)
	
	def __InitMessageAuthor(self, message: discord.Message) -> None:
		if message.author.id not in self.UserIdToPoints:
			self.UserIdToPoints[message.author.id] = self.GetT()
			# Logger.Log(f"New user: <@{message.author.id}> {message.author.name}", Logger.OKBLUE)
			# Logger.Log(f"First message:")
			# Logger.Log(f"{Logger.GetFormattedMessage(message)}")

	async def __GetReactionFromMessage(self, message: discord.Message) -> discord.Reaction:
		emoji = [r for r in message.reactions if hasattr(r.emoji, "name") and r.emoji.name == self.__emojiName]
		if len(emoji) > 1:
			Logger.Log(f"Found {len(emoji)} reactions of the same name, somehow! Not sure what to do", Logger.ERROR)
			return None
		return emoji[0] if len(emoji) == 1 else None

	async def __GetReactionUserIds(self, reaction: discord.Reaction) -> list:
		if type(reaction) == discord.Reaction:
			return [u.id for u in await reaction.users().flatten()]
		elif type(reaction) == ChannelCacher.SerializableReaction:
			return reaction.userIds

	def MessageAuthorReacted(self, message: discord.Message, reactionUsers: list) -> bool:
		return message.author.id in reactionUsers

	async def GetCountsFrom(self, message: discord.Message, reaction: discord.Reaction) -> T:
		raise NotImplementedError("Unimplemented in parent")

	def GetT(self) -> T:
		raise NotImplementedError("Unimplemented in parent")

class MessageAuthorUpvoteCounter(PointCounter[SelfAndTotalPoints]):
	def __init__(self):
		super().__init__("upnion")

	async def GetCountsFrom(self, message: discord.Message, reaction: discord.Reaction) -> SelfAndTotalPoints:
		points = SelfAndTotalPoints()
		points.Total += reaction.count
		if self.MessageAuthorReacted(message, self.ReactionUserIds):
			points.Self -= 1
			points.Total -= 2 ## Since we added a point from ourself above, remove it and one more here. Shame on us.
			Logger.Log("Self vote: " + Logger.GetFormattedMessage(message), Logger.WARNING)
		return points

	def GetT(self):
		return SelfAndTotalPoints()

class MessageAuthorDownvoteCounter(PointCounter[SelfAndTotalPoints]):
	def __init__(self):
		super().__init__("downion")

	async def GetCountsFrom(self, message: discord.Message, reaction: discord.Reaction) -> SelfAndTotalPoints:
		points = SelfAndTotalPoints()
		points.Total -= reaction.count
		if self.MessageAuthorReacted(message, self.ReactionUserIds):
			points.Self -= 1
		return points

	def GetT(self):
		return SelfAndTotalPoints()

class MessageAuthorRandomVoteCounter(PointCounter[SelfAndTotalPoints]):
	def __init__(self):
		super().__init__("prego")

	async def GetCountsFrom(self, message: discord.Message, reaction: discord.Reaction) -> SelfAndTotalPoints:
		points = SelfAndTotalPoints()
		if self.MessageAuthorReacted(message, self.ReactionUserIds):
			amount = random.randint(-5, 5)
			points.Total += amount
			points.Self += amount
			Logger.Log(f"Prego ({amount}): " + Logger.GetFormattedMessage(message), Logger.WARNING)
		return points

	def GetT(self):
		return SelfAndTotalPoints()

class MessageAuthorPointCounters:
	def __init__(self):
		self.UpvoteCounter = MessageAuthorUpvoteCounter()
		self.DownvoteCounter = MessageAuthorDownvoteCounter()
		self.RandomCounter = MessageAuthorRandomVoteCounter()

	async def Count(self, message: discord.Message) -> None:
		await self.UpvoteCounter.Count(message)
		await self.DownvoteCounter.Count(message)
		await self.RandomCounter.Count(message)

	def GetUserIdToPoints(self) -> dict:
		return (self.UpvoteCounter + self.DownvoteCounter + self.RandomCounter).UserIdToPoints

class ChannelLeaderboard:
	## Never go look before this, because voting didn't exist then
	EarliestVote = datetime.datetime(2020, 1, 30)

	def __init__(self):
		self.MessageAuthorPointCounters = MessageAuthorPointCounters()
		self.LastUtcSyncTime = None

	async def AddCount(self, message: discord.Message) -> None:
		await self.MessageAuthorPointCounters.Count(message)

	def GetMessageAuthorPoints(self) -> dict:
		return self.MessageAuthorPointCounters.GetUserIdToPoints()

class LeaderboardCollection:
	__channelIdToLeaderboard = {}
	__channelCacher = ChannelCacher.ChannelCacher()

	async def PrintMessageAuthorPoints(self, bot, channel: discord.TextChannel) -> None:
		await self.__BuildLeaderboard(channel)

		toPrint = self.__channelIdToLeaderboard[channel.id].GetMessageAuthorPoints()
		await self.__OutputLeaderboard(channel, bot.GetRawClient(), toPrint)

	async def __BuildLeaderboard(self, channel: discord.TextChannel) -> None:
		#if channel.id not in self.__channelIdToLeaderboard:
			self.__InitLeaderboard(channel)

		#if self.__channelIdToLeaderboard[channel.id].LastUtcSyncTime is None:
			await self.__CreateLeaderboardFromScratch(channel)
		#else:
		#	await self.__UpdateLeaderboard(channel)

	def __InitLeaderboard(self, channel: discord.TextChannel) -> None:
		self.__channelIdToLeaderboard[channel.id] = ChannelLeaderboard()


	## TODO: Create and update could be consolidated if I set LastUtcSyncTime to EarliestVote by default
	async def __CreateLeaderboardFromScratch(self, channel: discord.TextChannel) -> None:
		await Screamer.Scream(channel, "One second, this might take a while...")

		thisBoard = self.__channelIdToLeaderboard[channel.id]
		thisBoard.LastUtcSyncTime = datetime.datetime.utcnow()

		await self.__channelCacher.Update(channel, after=thisBoard.EarliestVote)

		numMessages = 0
		async with channel.typing():
			for message in self.__channelCacher.IterateCache(channel, after=thisBoard.EarliestVote):
				numMessages += 1
				await thisBoard.AddCount(message)

		self.__channelIdToLeaderboard[channel.id] = thisBoard
		Logger.Log(f"Leaderboard rebuild successful ({numMessages} messages)", Logger.SUCCESS)

	async def __UpdateLeaderboard(self, channel: discord.TextChannel) -> None:
		thisBoard = self.__channelIdToLeaderboard[channel.id]
		lastUtcSyncTime = thisBoard.LastUtcSyncTime
		thisBoard.LastUtcSyncTime = datetime.datetime.utcnow()

		await self.__channelCacher.Update(channel, after=thisBoard.EarliestVote)

		formattedLast = lastUtcSyncTime.isoformat(timespec="seconds")
		formattedNow = thisBoard.LastUtcSyncTime.isoformat(timespec="seconds")
		Logger.Log(f"Updating leaderboard: {formattedLast} -> {formattedNow}", Logger.OKBLUE)

		numMessages = 0
		async with channel.typing():
			for message in self.__channelCacher.IterateCache(channel, after=thisBoard.EarliestVote):
				if message.created_at > lastUtcSyncTime:
					numMessages += 1
					await thisBoard.AddCount(message)
				else:
					Logger.Log(f"I don't think (after=) works how I expect: {Logger.GetFormattedMessage(message)}", Logger.ERROR)

		self.__channelIdToLeaderboard[channel.id] = thisBoard
		Logger.Log("Leaderboard update successful", Logger.SUCCESS)
		await Screamer.Scream(channel, "Updated point totals of {} messages.".format(numMessages))

	async def __UserToName(self, botClient, userId):
		try:
			return (await botClient.fetch_user(userId)).name
		except:
			return f"Unknown <{userId}>"

	async def __OutputLeaderboard(self, channel: discord.TextChannel, botClient: discord.Client, toPrint: dict) -> None:
		botId = botClient.user.id
		userNum = 1

		sortedNamesToPoints = [(await self.__UserToName(botClient, userId), points) for userId, points in \
			sorted(toPrint.items(), key=lambda item: item[1], reverse=True) \
			if userId != botId]

		longestName = max([len(nameAndPoints[0]) for nameAndPoints in sortedNamesToPoints])
		output = "Here you go:\n```"
		for userName, points in sortedNamesToPoints:
			additionalSpaces = " " * (longestName - len(userName) + 1)
			output += f"{userNum}    {userName}{additionalSpaces}: {str(points)}\n"
			userNum += 1
		output += "```"

		await Screamer.Scream(channel, output)

	## TODO: Not a public API
	async def CacheChannel(self, channel: discord.TextChannel, force_rebuild):
		await self.__channelCacher.Update(channel, force_rebuild)
