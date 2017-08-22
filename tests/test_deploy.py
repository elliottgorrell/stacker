import pytest

from stacker import deploy


def test_error_thrown_on_incorrect_config_file_format():
    with pytest.raises(deploy.DeployException):
        executor = deploy.DeployExecutor()
        executor.load_parameters("config.txt")