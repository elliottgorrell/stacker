from unittest import TestCase

import pytest
from mock import call, MagicMock

from stacker import ami
from stacker.cf_helper import utils as cf_utils

class AMIExecutorTest(TestCase):

    def test_no_parameters(self):

        executor = ami.AMIExecutor(None)

        with pytest.raises(cf_utils.DeployException) as ex:
            executor.execute()

        self.assertEqual("--artifact-id or --ami-id must be supplied for the search", ex.value.message)

    def test_by_artifact_id_no_result(self):

        executor = ami.AMIExecutor(None)
        executor.ec2_client = MagicMock()

        mock_response = {"Images": []}
        executor.ec2_client.describe_images = MagicMock(return_value=mock_response)

        with pytest.raises(cf_utils.DeployException) as ex:
            result = executor.execute(artifact_id="artifact")

        self.assertEqual([call.describe_images(Filters=[{'Values': ['artifact'], 'Name': 'tag:ArtifactID'}])],
                         executor.ec2_client.mock_calls)

        self.assertEqual("No images found for search 'artifact'", ex.value.message)

    def test_by_artifact_id_with_single_result(self):

        executor = ami.AMIExecutor(None)
        executor.ec2_client = MagicMock()

        mock_response = {"Images": [{"ImageId": "id-1234", "Name": "mock-image", "CreationDate": "today"}]}
        executor.ec2_client.describe_images = MagicMock(return_value=mock_response)

        executor.execute(artifact_id="artifact")

        self.assertEqual([call.describe_images(Filters=[{'Values': ['artifact'], 'Name': 'tag:ArtifactID'}])],
                         executor.ec2_client.mock_calls)

    def test_by_artifact_id_with_duplicate_result(self):

        executor = ami.AMIExecutor(None)
        executor.ec2_client = MagicMock()

        mock_response = {"Images": [{"ImageId": "id-1234", "Name": "mock-image", "CreationDate": "today"},
                                    {"ImageId": "id-1235", "Name": "mock-image", "CreationDate": "today"}]}

        executor.ec2_client.describe_images = MagicMock(return_value=mock_response)

        with pytest.raises(cf_utils.DeployException) as ex:
            result = executor.execute(artifact_id="artifact")

        self.assertEqual([call.describe_images(Filters=[{'Values': ['artifact'], 'Name': 'tag:ArtifactID'}])],
                         executor.ec2_client.mock_calls)

        self.assertEqual("More than 1 image found for search 'artifact'", ex.value.message)

    def test_by_ami_id_with_no_result(self):

        executor = ami.AMIExecutor(None)
        executor.ec2_client = MagicMock()

        mock_response = {"Images": []}
        executor.ec2_client.describe_images = MagicMock(return_value=mock_response)

        with pytest.raises(cf_utils.DeployException) as ex:
            executor.execute(ami_id="ami-1234")

        self.assertEqual([call.describe_images(ImageIds=['ami-1234'])],
                         executor.ec2_client.mock_calls)

        self.assertEqual("No images found for search 'ami-1234'", ex.value.message)

    def test_by_ami_id_with_single_result(self):

        executor = ami.AMIExecutor(None)
        executor.ec2_client = MagicMock()

        mock_response = {"Images": [{"ImageId": "id-1234", "Name": "mock-image", "CreationDate": "today"}]}
        executor.ec2_client.describe_images = MagicMock(return_value=mock_response)

        executor.execute(ami_id="ami-1234")

        self.assertEqual([call.describe_images(ImageIds=['ami-1234'])],
                         executor.ec2_client.mock_calls)

    def test_by_ami_id_with_multiple_results(self):
        executor = ami.AMIExecutor(None)
        executor.ec2_client = MagicMock()

        mock_response = {"Images": [{"ImageId": "id-1234", "Name": "mock-image", "CreationDate": "today"},
                                    {"ImageId": "id-1235", "Name": "mock-image", "CreationDate": "today"}]}
        executor.ec2_client.describe_images = MagicMock(return_value=mock_response)

        with pytest.raises(cf_utils.DeployException) as ex:
            executor.execute(ami_id="ami-1234")

        self.assertEqual([call.describe_images(ImageIds=['ami-1234'])],
                         executor.ec2_client.mock_calls)

        self.assertEqual("More than 1 image found for search 'ami-1234'", ex.value.message)