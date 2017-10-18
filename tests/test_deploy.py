import pytest
import os
from mock import MagicMock
from stacker import deploy


cf_json = os.path.join(os.path.dirname(__file__),'resources/cloudformation.json')
cf_yaml_functions = os.path.join(os.path.dirname(__file__), 'resources/cf_functions.yaml')
cf_json_functions = os.path.join(os.path.dirname(__file__), 'resources/cf_functions.json')
config_json = os.path.join(os.path.dirname(__file__), 'resources/config.json')

def test_error_thrown_on_incorrect_config_file_format():
    with pytest.raises(deploy.DeployException):
        executor = deploy.DeployExecutor()
        executor.load_parameters("config.txt")

def test_load_json_cloudformation():
    executor = deploy.DeployExecutor()
    executor.load_cloudformation(cf_json)

def test_deploy_with_no_config_file():
    executor = deploy.DeployExecutor()

    executor.cf_client = MagicMock()

    executor.cf_client.create_change_set = MagicMock()
    executor.cf_client.wait_for_change_set_to_complete = MagicMock()

    executor.execute(stack_name="test-stack",template_name=cf_json)

def test_deploy_with_json_config():
    executor = deploy.DeployExecutor()

    executor.cf_client = MagicMock()

    executor.cf_client.create_change_set = MagicMock()
    executor.cf_client.wait_for_change_set_to_complete = MagicMock()

    executor.execute(stack_name="test-stack",template_name=cf_json, config_filename=config_json, create=True)

    executor.cf_client.create_change_set.assert_called()
    executor.cf_client.wait_for_change_set_to_complete.assert_called()


# Tests that we can parse yaml containing Cloudformation functions
def test_parse_yaml_cf_with_functions():
    executor = deploy.DeployExecutor()
    cloudformation_map = executor.load_cloudformation(cf_yaml_functions)

    assert cloudformation_map['Resources']['MyInstance']['Properties']['ImageId'] == "ami-1b814f72"

# Tests that we can parse json containing Cloudformation functions
def test_parse_json_cf_with_functions():
    executor = deploy.DeployExecutor()
    cloudformation_map = executor.load_cloudformation(cf_json_functions)

    assert cloudformation_map['Resources']['MyInstance']['Properties']['ImageId'] == "ami-1b814f72"

# # Tests that we can deploy a JSON Cloudformation the full way
# def test_full_deploy_json():
#     executor = deploy.DeployExecutor()
#
#     executor.cf_client.create_change_set = MagicMock()
#     executor.cf_client.wait_for_change_set_to_complete = MagicMock()
#     executor.cf_client.describe_change_set = MagicMock(return_value={'status':'running'})
#     executor.cf_client.execute_change_set = MagicMock()
#     executor.cf_client.describe_stacks = MagicMock()
#
#     executor.execute(stack_name="test-stack",template_name=cf_json, config_filename=config_json, create=True)
#
#     executor.cf_client.create_change_set.assert_called()
#     executor.cf_client.wait_for_change_set_to_complete.assert_called()

def test_all_extra_config_options_provided():
    executor = deploy.DeployExecutor()

    config_params = executor.resolve_config_params(None,None,["animal=dog","house=blue"],"ami-ac3nf6",None)

    assert config_params['animal'] == 'dog'
    assert config_params['house'] == 'blue'
    assert config_params['AMIParam'] == 'ami-ac3nf6'

def test_ami_tag_config_provided():
    executor = deploy.DeployExecutor()

    executor.get_ami_id_by_tag = MagicMock(return_value="ami-ac3nf6")

    config_params = executor.resolve_config_params(None,None,None,None,"atag")


    assert config_params['AMIParam'] == 'ami-ac3nf6'
    executor.get_ami_id_by_tag.call_args.assert_called_with('atag')