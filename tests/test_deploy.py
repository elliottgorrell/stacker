from unittest import TestCase

import pytest

from stacker import deploy


class DeployExecutorTest(TestCase):

    def test_error_thrown_on_incorrect_config_file_format(self):
        with pytest.raises(deploy.DeployException):
            executor = deploy.DeployExecutor()
            executor.load_parameters("config.txt")

    def test_