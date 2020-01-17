class MessageSanitizer:
	def __init__(self, botId):
		self.__botId = botId
		self.__botMentions = [
			"<@{}>".format(botId),
			"<@!{}>".format(botId)
		]

	def StartsWithBotMention(self, content):
		return any([content.strip().startswith(mention) for mention in self.__botMentions])

	def RemoveBotMentionFromStart(self, content):
		whichMentions = [i for i, m in enumerate(self.__botMentions) if content.startswith(m)]
		return content[len(whichMentions) > 0 and len(self.__botMentions[whichMentions[0]]):].strip()

	def SanitizeContent(self, content):
		return self.RemoveBotMentionFromStart(content)
