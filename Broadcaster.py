async def Broadcast(channel, message, printToConsole=True):
	if printToConsole:
		print("Broadcaster: ", message)
	await channel.send(message)

## Idk, I might add other types of broadcast. Like whispering to users or something
