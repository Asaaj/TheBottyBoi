import datetime

HEADER = "\033[95m"

BLUE = "\033[94m"
OKBLUE = BLUE + "- "

CHECK = u"\u2713"
GREEN = "\033[92m"
SUCCESS = GREEN + CHECK + " "

YELLOW = "\033[93m"
WARNING = YELLOW + "! "

X = u"\u2717"
RED = "\033[91m"
ERROR = RED + X + " "

END = "\033[0m"

BOLD = "\033[1m"
UNDERLINE = "\033[4m"

__OverridingColors__ = [OKBLUE, SUCCESS, WARNING, ERROR]
__OverridingToPlainColor__ = {
	OKBLUE: BLUE,
	SUCCESS: GREEN,
	WARNING: YELLOW,
	ERROR: RED
}

def AsHeader(message):
	return HEADER + message + END

def AsOk(message):
	return BLUE + message + END

def AsSuccess(message):
	return GREEN + message + END

def AsWarning(message):
	return YELLOW + message + END

def AsError(message):
	return RED + message + END

def Bold(message):
	return BOLD + message + END

def Underline(message):
	return UNDERLINE + message + END

def GetFormattedTime(time=None):
	if time is None:
		time = datetime.datetime.now()
	timeFormat = "%y-%m-%d %H:%M:%S.%f"
	return time.strftime(timeFormat)[:-3]

def GetFormattedMessage(message):
	formattedCreateTime = GetFormattedTime(message.created_at)
	return AsHeader(f"{message.author} ") + AsOk(f"<{formattedCreateTime}>") + f": {message.content}"

def Log(message, colors=''):
	message = str(message)
	output = colors + message + END

	if all(c not in colors for c in __OverridingColors__):
		output = "  " + output

	## This should probably take the last of the colors passed in, and use that if it's overriding.
	## Instead, it just looks at the global overriding colors in reverse order. Meh, oh well
	overridingColors = [c for c in reversed(__OverridingColors__) if c in colors]
	if len(overridingColors) > 0:
		firstFound = overridingColors[0]
		output = output.replace(END, __OverridingToPlainColor__[firstFound])
		output = output + END

	timestampColor = BLUE
	if ERROR in colors:
		timestampColor = RED + BOLD

	timestampText = "[" + GetFormattedTime() + "] "

	## Pad the additional lines of a multi-line message, since they don't get timestamps
	optionalPadding = " " * (len(timestampText) + 2)
	output = output.replace("\n", "\n" + optionalPadding)
	output = timestampColor + timestampText + END + output
	print(output)
