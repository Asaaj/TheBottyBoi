import asyncio, sys, unittest
from io import StringIO

import Screamer, TestStructures

## I'm not sure how to run async functions from a synchronous method in an asynchronous context

# class TestTestClasses(unittest.TestCase):
# 	def setUp(self):
# 		self.__old_stdout = sys.stdout
# 		sys.stdout = self.__stdout = StringIO()

# 	def tearDown(self):
# 		sys.stdout = self.__old_stdout

# 	def test_Send(self):
# 		async def test():
# 			message = "MESSAGE"
# 			channelName = "CHANNEL"
# 			channel = TestStructures.TestChannel(channelName)
			
# 			await channel.send(message)

# 			expected = channel.FormatMessage(channelName, message).strip()
# 			actual = self.__stdout.getvalue().strip()
# 			self.assertEqual(expected, actual)

# 		asyncio.run(test())

# class TestScreamer(unittest.TestCase):
# 	def setUp(self):
# 		self.__old_stdout = sys.stdout
# 		sys.stdout = self.__stdout = StringIO()

# 	def tearDown(self):
# 		sys.stdout = self.__old_stdout

# 	def test_Broadcast(self):
# 		async def test():
# 			message = "MESSAGE"
# 			channelName = "CHANNEL"
# 			channel = TestStructures.TestChannel(channelName)

# 			await Screamer.Scream(channel, message, printToConsole=False)

# 			expected = channel.FormatMessage(channelName, message).strip()
# 			actual = self.__stdout.getvalue().strip()
# 			self.assertEqual(expected, actual)

# 		asyncio.run(test())

if __name__ == "__main__":
	unittest.main()
