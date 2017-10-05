from unittest import TestCase

import pytest
import os
from mock import MagicMock
from stacker import deploy
import logging
from testfixtures import LogCapture


class DeployExecutorTest(TestCase):

    cf_json = os.path.join(os.path.dirname(__file__),'resources/cloudformation.json')
    cf_yaml_functions = os.path.join(os.path.dirname(__file__), 'resources/cf_functions.yaml')
    cf_json_functions = os.path.join(os.path.dirname(__file__), 'resources/cf_functions.json')
    config_json = os.path.join(os.path.dirname(__file__), 'resources/config.json')
    config_yaml = os.path.join(os.path.dirname(__file__), 'resources/config.yaml')

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

        executor.execute(stack_name="test-stack",template_name=self.cf_json)

    def test_deploy_with_json_config(self):
        executor = deploy.DeployExecutor()

        executor.cf_client = MagicMock()

        executor.cf_client.create_change_set = MagicMock()
        executor.cf_client.wait_for_change_set_to_complete = MagicMock()

        executor.execute(stack_name="test-stack",template_name=self.cf_json, config_filename=self.config_json, create=True)

        executor.cf_client.create_change_set.assert_called()
        executor.cf_client.wait_for_change_set_to_complete.assert_called()


    # Tests that we can parse yaml containing Cloudformation functions
    def test_deploy_yaml_cf_with_functions(self):
        executor = deploy.DeployExecutor()

        executor.cf_client = MagicMock()

        executor.cf_client.create_change_set = MagicMock()
        executor.cf_client.wait_for_change_set_to_complete = MagicMock()

        executor.execute(stack_name="test-stack", template_name=self.cf_yaml_functions, config_filename=self.config_json, create=True)

        executor.cf_client.create_change_set.assert_called()
        executor.cf_client.wait_for_change_set_to_complete.assert_called()

    # Tests that we can parse json containing Cloudformation functions
    def test_deploy_json_cf_with_functions(self):
        executor = deploy.DeployExecutor()

        executor.cf_client = MagicMock()

        executor.cf_client.create_change_set = MagicMock()
        executor.cf_client.wait_for_change_set_to_complete = MagicMock()

        executor.execute(stack_name="test-stack",template_name=self.cf_json_functions, config_filename=self.config_json, create=True)

        executor.cf_client.create_change_set.assert_called()
        executor.cf_client.wait_for_change_set_to_complete.assert_called()

    def test_debug_messages_print(self):
        executor = deploy.DeployExecutor()
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

        # Test we get correct message when loading parameters in debug mode
        with LogCapture() as log:
            executor.load_parameters(config_filename=self.config_yaml, scope='DB')
            log.check(
                ('root','INFO','Resolving config file '+self.config_yaml+' using scope DB')
            )

