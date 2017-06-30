__author__ = "Steve Mactaggart"

import base64
import json
import re
import sys
import traceback
from datetime import datetime

import boto3
import botocore
import yaml

from cf_helper import secure_print
from cf_helper.utils import DeployException, CloudFormationUtil, STSUtil

class DeployExecutor(object):
    REGEX_YAML = re.compile('.+\.yaml|.+.yml')
    REGEX_JSON = re.compile('.+\.json')

    def execute(self, stack_name, config_filename, template_name,
                role, add_parameters, version, ami_id, ami_tag_value,
                scope, create=False, delete=False, dry_run=False,
                debug=False):

        try:

            if config_filename is not None:
                if debug:
                    print "Resolving config file {} using scope {}".format(config_filename, scope)

                config_params = self.load_parameters(config_filename, scope)

            # First override any of the defaults with those supplied at the command line
            if add_parameters is None or len(add_parameters) == 0:
                adds = {}
            else:
                adds = dict(item.split("=") for item in add_parameters)
                config_params.update(adds)

            cf_client, ec2_client, kms_client = self.get_boto3_clients(role)
            cf_util = CloudFormationUtil(cf_client)

            if version:
                config_params["VersionParam"] = version
            else:
                version = datetime.now().isoformat('-').replace(":", "-")

            if ami_id:
                config_params["AMIParam"] = ami_id
            elif ami_tag_value:
                config_params["AMIParam"] = self.get_ami_id_by_tag(ami_tag_value, ec2_client)


            secrets = []
            for key in config_params:
                # Check that config file doesn't have scopes (Parameters for more than one Cloudformation file)
                if type(config_params[key]) is dict:
                    raise DeployException("Objects were found with nested values, you will need to specify which set of parameters to use with \"--scope <object_name>\"".format(key))

                # Check if the value contains KMS encrypted value (KMSEncrypted /KMSEncrypted tag pair)
                # if true, decrypt and replace the value
                encryption_check = re.search('KMSEncrypted(.*)/KMSEncrypted', config_params[key])

                if encryption_check:
                    decrypted_value = kms_client.decrypt(CiphertextBlob=base64.b64decode(encryption_check.group(1)))["Plaintext"]
                    config_params[key] = decrypted_value
                    secrets += [decrypted_value]

            try:
                with open(template_name, "r") as myfile:
                    raw_cloudformation = myfile.read()
            except Exception as error:
                raise DeployException("Unable to locate CloudFormation template ''{}'\n{}"
                                      .format(template_name, error))

            cloudformation = self.load_cloudformation_file(template_name, raw_cloudformation)

            # Go through parameters needed and fill them in from the parameters provided in the config file
            # They need to be re-formated from the python dictionary into boto3 useable format
            parameters = self.import_params_from_config(cloudformation, config_params, create, secrets)

            print "Using stack parameters"
            # This hides any encrypted values that were decrypted with KMS
            print secure_print(json.dumps(parameters, indent=2), secrets)

            if create:
                change_set_name = "Create-{}".format(version.replace(".", "-"))
                changeset = self.get_change_set(stack_name, raw_cloudformation, parameters, change_set_name, cf_client, create)

            elif delete:
                if not dry_run:
                    result = cf_client.delete_stack(StackName=stack_name)
                    print result
                else:
                    print "[Dry-Run] Not deleting stack."
            else:
                change_set_name = "Update-{}".format(version.replace(".", "-"))
                changeset = self.get_change_set(stack_name, raw_cloudformation, parameters, change_set_name, cf_client)

            if changeset is not None:
                cf_util.wait_for_change_set_to_complete(change_set_name=change_set_name,
                                                                    stack_name=stack_name,
                                                                    debug=False)

                change_set_details = cf_client.describe_change_set(ChangeSetName=change_set_name,
                                                                   StackName=stack_name)

                self.print_change_set(change_set_details)

                if dry_run:
                    response = cf_client.delete_change_set(ChangeSetName=change_set_name,
                                                           StackName=stack_name)
                else:
                    response = cf_client.execute_change_set(ChangeSetName=change_set_name,
                                                            StackName=stack_name)

                    cf_util.wait_for_deploy_to_complete(stack_name=stack_name)


        except botocore.exceptions.ClientError as e:
            if str(e) == "An error occurred (ValidationError) when calling the UpdateStack operation: No updates are to be performed.":
                print "No stack update required - CONTINUING"
            else:
                print "Unexpected error: %s" % e
                sys.exit(1)
        except DeployException as error:
            print "ERROR: {0}".format(error)
            sys.exit(1)
        except Exception as error:
            traceback.print_exc(file=sys.stdout)
            traceback.print_stack(file=sys.stdout)
            print "ERROR: {0}".format(error)
            traceback.print_exc(file=sys.stdout)
            sys.exit(1)

    def get_boto3_clients(self, role = None):
        if role:
            sts = STSUtil(sts_arn=role, debug=True)
            credentials = sts.authenticate_role()['Credentials']

            cf_client = boto3.client('cloudformation',
                                     aws_access_key_id=credentials['AccessKeyId'],
                                     aws_secret_access_key=credentials['SecretAccessKey'],
                                     aws_session_token=credentials['SessionToken'], )
            ec2_client = boto3.client('ec2',
                                      aws_access_key_id=credentials['AccessKeyId'],
                                      aws_secret_access_key=credentials['SecretAccessKey'],
                                      aws_session_token=credentials['SessionToken'], )
            kms_client = boto3.client('kms',
                                      aws_access_key_id=credentials['AccessKeyId'],
                                      aws_secret_access_key=credentials['SecretAccessKey'],
                                      aws_session_token=credentials['SessionToken'], )

        # If no role is specified the current environments will be used
        else:
            cf_client = boto3.client('cloudformation')
            ec2_client = boto3.client('ec2')
            kms_client = boto3.client('kms')

        return cf_client, ec2_client, kms_client

    def load_parameters(self, config_filename, scope):
        try:
            with open(config_filename) as config_file:
                if re.match(self.REGEX_YAML, config_filename):
                    config_data = yaml.load(config_file)
                elif re.match(self.REGEX_JSON, config_filename):
                    config_data = json.load(config_file)
                else:
                    raise DeployException("Config must be a YAML or JSON file")

            if scope is not None:
                if scope not in config_data:
                    raise DeployException("Cannot find scope '{}' within the '{}' configuration file."
                                          .format(scope, config_filename))
                parameters = config_data[scope]
            else:
                parameters = config_data

            return parameters

        except DeployException as ex:
            raise ex

        except Exception as error:
            raise DeployException("Unable to open config file '{}'\n{}".format(config_filename, error))

    def get_ami_id_by_tag(self, ec2_client, ami_tag_value):
        images = ec2_client.describe_images(Filters=[
            {'Name': 'tag:ArtifactID',
             'Values': [ami_tag_value]}
        ])['Images']

        if len(images) == 0:
            raise DeployException("No images found for search '{}'".format(ami_tag_value))
        elif len(images) > 1:
            print images
            raise DeployException("More than 1 image found for search '{}'".format(ami_tag_value))
        else:
            ami_id = images[0]["ImageId"]
            print "Located AMI {} - {} created {}".format(ami_id, images[0]['Name'], images[0]['CreationDate'])

        return ami_id

    def load_cloudformation_file(self, template_name, raw_cloudformation):
        try:
            if re.match(self.REGEX_YAML, template_name):
                cloudformation = yaml.load(raw_cloudformation)
            elif re.match(self.REGEX_JSON, template_name):
                cloudformation = json.load(raw_cloudformation)
            else:
                raise DeployException("Cloudformation template must be a JSON or YAML file")

        except Exception as error:
            raise DeployException("Unable to parse CloudFormation template '{}'\n{}"
                                  .format(template_name, error))

        if cloudformation is None:
            raise DeployException("It looks like the CloudFormation template file is empty")

        return cloudformation

    def import_params_from_config(self, cloudformation, config_params, create, secrets = []):
        parameters = []
        if 'Parameters' in cloudformation:
            for param, values in cloudformation['Parameters'].items():
                if param in config_params:
                    parameters += [{
                        "ParameterKey": param,
                        "ParameterValue": config_params[param]
                    }]
                else:
                    # If this is first deployment of stack we try and use a default provided in the CF
                    if create:
                        defaultValue = values.get('Default')
                        if defaultValue is not None:
                            parameters += [{
                                "ParameterKey": param,
                                "ParameterValue": defaultValue
                            }]
                        # There is no default and there is no previous value to use so throw an error
                        else:
                            raise DeployException("Cannot CREATE new stack with missing parameter {}".format(param))
                            sys.exit(-1)
                    # This is an update of existing stack so use current value
                    else:
                        print "Using current stack value for parameter {}".format(param)
                        parameters += [{
                            "ParameterKey": param,
                            "UsePreviousValue": True
                        }]
            return parameters
        else:
            print "Specified template has no stack parameters"

    def get_change_set(self, stack_name, cloudformation, parameters, change_set_name, cf_client, create = False):
        if create:
            changeset = cf_client.create_change_set(
                StackName=stack_name,
                TemplateBody=cloudformation,
                Parameters=parameters,
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                ChangeSetName=change_set_name,
                ChangeSetType="CREATE"
                )
        else:
            changeset = cf_client.create_change_set(
                StackName=stack_name,
                TemplateBody=cloudformation,
                Parameters=parameters,
                Capabilities=[
                    'CAPABILITY_IAM',
                ],
                ChangeSetName=change_set_name,
            )

        return changeset

    def print_change_set(self, change_set_details):
        if len(change_set_details['Changes']) > 0:
            print "-------------------------------"
            print "CloudFormation changes to apply"
            print "-------------------------------"
            for x in change_set_details['Changes']:
                change = x["ResourceChange"]

                if change["Action"] == "Add":
                    replace_mode = "New resource"
                elif change["Action"] == "Modify":
                    replace_mode = change["Replacement"]
                    if replace_mode == "False":
                        replace_mode = "Update in place"
                    elif replace_mode == "False":
                        replace_mode = "Full replacement"
                    elif replace_mode == "Conditional":
                        replace_mode = "Conditionally replace"
                else:
                    replace_mode = "Delete resource"

                change_mode = "[{} - {}]".format(change["Action"], replace_mode)

                print "{} {}/{} ({})".format(change_mode.ljust(34), change["LogicalResourceId"],
                                             change.get("PhysicalResourceId", ""), change["ResourceType"])

            print ""
        else:
            print "No CloudFormation changes detected"
