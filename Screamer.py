import datetime

import Logger
ReloadableImports = [ Logger ]

async def Scream(channel, message, printToConsole=True):
	if printToConsole:
		Logger.Log(Logger.AsHeader(f"Screamer") + f":  {message}")
	await channel.send(message, tts=False)
