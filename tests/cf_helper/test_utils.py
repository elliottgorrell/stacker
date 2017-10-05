from unittest import TestCase

import pytest
import os
from mock import MagicMock
from stacker.cf_helper import utils
import logging
from testfixtures import LogCapture

class DeployExecutorTest(TestCase):
    def test_debug_messages_print(self):
        cf_client = MagicMock()
        cf_client.describe_change_set = MagicMock(return_value=dict({'Status':'READY'}))
        cf_util = utils.CloudFormationUtil(cf_client)

        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Test we get correct message when loading parameters in debug mode
        with LogCapture() as log:
            cf_util.wait_for_change_set_to_complete('test-stack','test-set')
            log.check(
                ('root', 'INFO', '(1/30) - ChangeSet [test-set] for test-stack is READY')
        )