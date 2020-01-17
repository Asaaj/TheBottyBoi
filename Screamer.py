async def Scream(channel, message, printToConsole=True):
	if printToConsole:
		print("Screamer: ", message)
	await channel.send(message)
