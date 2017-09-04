from unittest import TestCase

import pytest
import os
from mock import MagicMock
from stacker import deploy


class DeployExecutorTest(TestCase):

    cf_json = os.path.join(os.path.dirname(__file__),'resources/cloudformation.json')

    def test_error_thrown_on_incorrect_config_file_format(self):
        with pytest.raises(deploy.DeployException):
            executor = deploy.DeployExecutor()
            executor.load_parameters("config.txt")

    def test_load_json_cloudformation(self):
        executor = deploy.DeployExecutor()
        executor.load_cloudformation(self.cf_json)

    def test_deploy_with_no_config_file(self):
        executor = deploy.DeployExecutor()

        executor.cf_client = MagicMock()

        executor.cf_client.create_change_set = MagicMock()
        executor.cf_client.wait_for_change_set_to_complete = MagicMock()

        executor.execute(stack_name="test-stack",template_name=self.cf_json,dry_run=True)

        executor.cf_client.create_change_set.assert_called()
        executor.cf_client.wait_for_change_set_to_complete.assert_called()

