class Screamer:
	@staticmethod
	async def Scream(channel, message):
		print("Screamer: ", message)
		await channel.send(message)
