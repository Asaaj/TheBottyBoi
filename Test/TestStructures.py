#!/usr/bin/python3

class TestChannel:
	@staticmethod
	def FormatMessage(channelName, content):
		return "<{}>: {}".format(channelName, content)

	def __init__(self, name):
		self.__name = name

	async def send(self, message):
		print(TestChannel.FormatMessage(self.__name, message))

class TestUser:
	def __init__(self, name, id):
		self.name = name
		self.id = id

class TestMessage:
	def __init__(self, channel, user, content):
		self.channel = channel
		self.user = user
		self.content = content
		