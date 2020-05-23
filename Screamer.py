import datetime
async def Scream(channel, message, printToConsole=True):
	if printToConsole:
		print(f"Screamer <{datetime.datetime.now()}>:  {message}")
	await channel.send(message, tts=False)
