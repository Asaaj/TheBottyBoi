#!/usr/bin/python3

import json, unittest

import CommandFunctions, CommandValidation, Broadcaster
ReloadableImports = [ CommandFunctions, CommandValidation, Broadcaster ]

class TheBottyBoi:
	__commandFile = "command_map.json"
	__commandMap = None

	def __Log(self, msg):
		print("TheBottyBoi: " + msg)

	def __init__(self, botId):
		self.__botId = botId
		self.__RunUnitTests()
		self.__LoadCommandFile()

	def __RunUnitTests(self):
		loader = unittest.TestLoader()
		suite = loader.discover("Test/", pattern="Test*.py")
		self.__Log("Running {} unit tests".format(suite.countTestCases()))
		result = unittest.TextTestRunner().run(suite) 
		if not result.wasSuccessful():
			problems = result.failures
			problems.extend(result.errors)
			self.__Log("{} unit tests failed".format(len(problems)))
			raise AssertionError("Unit tests failed! Ran {} with {} failures".format(result.testsRun, len(problems)))
		self.__Log("Unit tests all ran successfully")

	def __LoadCommandFile(self):
		with open(self.__commandFile) as f:
			loadedJson = json.load(f)
			self.__commandMap = loadedJson['commands']
		
		mapValidator = CommandValidation.CommandMapValidator(self.__commandMap)
		mapValidator.Validate()

	def IsThisMessageSpecial(self, message):
		return False

	def DealWithIt(self, sanitizedContent, fullMessage):
		pass
