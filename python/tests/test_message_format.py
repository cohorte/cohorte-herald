#!/usr/bin/env python
# -- Content-Encoding: UTF-8 --
"""
Tests Herald Message Format
:author: Bassem Debbabi
"""

import herald.beans

import json


# Standard library
try:
    import unittest2 as unittest
except ImportError:
    import unittest


class MessageFormatTests(unittest.TestCase):
	"""
	Tests Herald Message Format
	"""

	def test_message_creation(self):
		msg = herald.beans.Message("mysubject")
		self.assertEqual(msg.subject, "mysubject")

	"""
	def test_to_json(self):
		msg1 = herald.beans.Message("mysubject")
		json_string_object1 = msg1.to_json()
		print(json_string_object1)				
	"""

	def test_msg_properties(self):
		msg = herald.beans.Message("mysubject", "mycontent", target_id="target_id", target_type="target_type", 
                       				sender_uid="sender_uid", send_mode="send_mode", replies_to="replies_to")
		self.assertEqual(msg.subject, "mysubject")
		self.assertEqual(msg.content, "mycontent")
		self.assertEqual(msg.target_id, "target_id")
		self.assertEqual(msg.target_type, "target_type")
		self.assertEqual(msg.target, "target_type:target_id")
		self.assertEqual(msg.sender_uid, "sender_uid")
		self.assertEqual(msg.send_mode, "send_mode")
		self.assertEqual(msg.replies_to, "replies_to")
		#self.assertEqual(msg.access, None)
		#self.assertEqual(msg.replied, False)
		self.assertIsNotNone(msg.uid)
		self.assertIsNotNone(msg.timestamp)

		extra = {"extra1key":"extra1value"}


		msg_rcv = herald.beans.MessageReceived(msg.uid, "mysubject_reply", "mycontent_reply", msg.sender_uid, msg.replies_to, "access", msg.timestamp, extra)
		self.assertEqual(msg_rcv.subject, "mysubject_reply")
		self.assertEqual(msg_rcv.content, "mycontent_reply")
		self.assertEqual(msg_rcv.sender_uid, "sender_uid")
		#self.assertEqual(msg_rcv.target_id, "target_id")
		#self.assertEqual(msg_rcv.target_type, "target_type")
		#self.assertEqual(msg_rcv.target, "target_type:target_id")		
		#self.assertEqual(msg_rcv.send_mode, "send_mode")
		self.assertEqual(msg_rcv.replies_to, "replies_to")
		self.assertEqual(msg_rcv.access, "access")
		msg_rcv.set_replied(True)
		self.assertEqual(msg_rcv.replied, True)


	def test_msg_transport_data(self):
		msg = herald.beans.Message("mysubject")
		msg.add_transport_data("url", "http://isandlatech.com")
		self.assertEqual(msg.get_transport_data("url"), "http://isandlatech.com")

	def test_msg_extra_info(self):
		msg = herald.beans.Message("mysubject")
		msg.add_extra("toto", "toti")
		self.assertEqual(msg.get_extra("toto"), "toti")

	def test_to_from_json(self):
		msg1 = herald.beans.Message("mysubject")
		json_string_object1 = msg1.to_json()
		print(json_string_object1)
		hash1 = hash(json_string_object1)
		msg2 = herald.beans.MessageReceived.from_json(json_string_object1)
		json_string_object2 = msg2.to_json()
		print(json_string_object2)
		hash2 = hash(json_string_object2)
		self.assertEqual(hash1, hash2)



# ------------------------------------------------------------------------------

if __name__ == "__main__":
    unittest.main()