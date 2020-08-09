#!/usr/bin/python3

import os, re

import Logger
ReloadableImports = [ Logger ]

class CommandStructure:
	RecognizedTypes = [ 
		"docreply",
		"function",
		"reply"
	]

	RequiredForAll = ["cmd", "type"]
	RequiredFor = {
		"docreply": [ "format" ],
		"function": [ ],
		"reply": [ "format" ]
	}

	OptionalForAll = [ "args", "hidden" ]
	OptionalFor = {
		"docreply": [ ],
		"function": [ "requires_client", "requires_bot" ],
		"reply": [ ]
	}

	## These names would cause collisions
	DisallowedTypes = [
		"special"
	]

def ValidateDocReplyCmd(cmdDef):
	fileFormat = "docreply/{}.txt"
	command = cmdDef["cmd"]
	filePath = fileFormat.format(command)
	if not os.path.isfile(filePath):
		raise IOError("File '{}' does not exist for command '{}'".format(filePath, command))

def ValidateReplyCmd(cmdDef):
	if "args" in cmdDef:
		for arg in cmdDef["args"]:
			if re.match(R"\[.*\]", arg):
				raise AttributeError("Reply command '{}' has optional argument '{}'".format(cmdDef["cmd"], arg[1:-1]))

class CommandMapValidator:
	__specialValidators = {
		"docreply": ValidateDocReplyCmd,
		"reply": ValidateReplyCmd
	}

	def __FormatLog(self, message):
		return Logger.AsHeader("CommandMapValidator") + ": " + message

	def __init__(self, cmdMap):
		self.__cmdMap = cmdMap

	def Validate(self):
		if self.__cmdMap is None:
			raise AttributeError("Empty command map")

		self.__ValidateSelf()
		try:
			for cmdDef in self.__cmdMap:
				self.__ValidateCmd(cmdDef)
		except Exception as e:
			Logger.Log(self.__FormatLog("Command map validation failed"), Logger.ERROR)
			raise e
		Logger.Log(self.__FormatLog("Command map validation successful"), Logger.SUCCESS)

	def __ValidateSelf(self):
		for cmdType in set(list(CommandStructure.RequiredFor.keys()) + list(CommandStructure.OptionalFor.keys())):
			if cmdType not in CommandStructure.RecognizedTypes:
				raise AttributeError("Type '{}' not in list of recognized command types".format(cmdType))

		if len(CommandStructure.RequiredForAll) != len(set(CommandStructure.RequiredForAll)):
			raise AttributeError("Command validator lists redundant required parameters")

		for cmdType in CommandStructure.RecognizedTypes:
			if set(CommandStructure.RequiredForAll) - set(CommandStructure.RequiredFor[cmdType]) != set(CommandStructure.RequiredForAll):
				raise AttributeError("Command type '{}' has redundant required parameters".format(cmdType))
			if set(CommandStructure.OptionalForAll) - set(CommandStructure.OptionalFor[cmdType]) != set(CommandStructure.OptionalForAll):
				raise AttributeError("Command type '{}' has redundant optional parameters".format(cmdType))
		
		for disallowed in CommandStructure.DisallowedTypes:
			if disallowed in CommandStructure.RecognizedTypes:
				raise AttributeError("Cannot have command type '{}'; it would cause a name collision".format(disallowed))
		
		Logger.Log(self.__FormatLog("ValidateSelf succeeded"), Logger.SUCCESS)

	def __ValidateCmd(self, cmdDef):
		self.__ValidateRequired(cmdDef)
		self.__ValidateOptional(cmdDef)
		self.__ValidateSpecial(cmdDef)

	def __ValidateRequired(self, cmdDef):
		for attr in CommandStructure.RequiredForAll:
			if not attr in cmdDef:
				if "cmd" in cmdDef.keys():
					raise AttributeError("Command '{}' missing required attribute '{}'".format(cmdDef["cmd"], attr))
				else:
					raise AttributeError("Command missing required attribute '{}'".format(attr))
		if cmdDef["type"] not in CommandStructure.RecognizedTypes:
			raise AttributeError("Unable to validate command of type '{}'".format(cmdDef["type"]))
		for attr in CommandStructure.RequiredFor[cmdDef["type"]]:
			if not attr in cmdDef:
				raise AttributeError("Command missing '{}'-type attribute '{}'".format(cmdDef["type"], attr))

	def __ValidateOptional(self, cmdDef):
		pass
		# for attr in cmdDef.keys():
		# 	if not attr in ??

	def __ValidateSpecial(self, cmdDef):
		cmdType = cmdDef["type"]
		if cmdType in self.__specialValidators.keys():
			self.__specialValidators[cmdType](cmdDef)

# class IncomingCommandValidator:

