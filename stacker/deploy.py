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

REGEX_YAML = re.compile('.+\.yaml|.+.yml')
REGEX_JSON = re.compile('.+\.json')

class DeployExecutor(object):

    def execute(self, stack_name, config_filename, template_name,
                role, add_parameters, version, ami_id, ami_tag_value,
                scope, create=False, delete=False, dry_run=False,
                debug=False):

        try:
            cf_params = []

            if config_filename is not None:
                if debug:
                    print "Resolving config file {} using scope {}".format(config_filename, scope)

                try:
                    with open(config_filename) as config_file:
                        if re.match(REGEX_YAML, config_filename):
                            config_data = yaml.load(config_file)
                        elif re.match(REGEX_JSON, config_filename):
                            config_data = json.load(config_file)
                        else:
                            raise DeployException("Config must be a YAML or JSON file")

                    if scope is not None:
                        if scope not in config_data:
                            raise DeployException("Cannot find scope '{}' within the '{}' configuration file.".format(scope, config_filename))
                        cf_params = config_data[scope]
                    else:
                        cf_params = config_data

                except DeployException as ex:
                    raise ex
                except Exception as error:
                    raise DeployException("Unable to open config file '{}'\n{}".format(config_filename, error))

            # First override any of the defaults with those supplied at the command line
            if add_parameters is None or len(add_parameters) == 0:
                adds = {}
            else:
                adds = dict(item.split("=") for item in add_parameters)
                cf_params.update(adds)

            if role:
                sts = STSUtil(sts_arn=role, debug=True)
                credentials = sts.authenticate_role()['Credentials']

                cf_client = boto3.client('cloudformation',
                                         aws_access_key_id=credentials['AccessKeyId'],
                                         aws_secret_access_key=credentials['SecretAccessKey'],
                                         aws_session_token=credentials['SessionToken'],)
                ec2_client = boto3.client('ec2',
                                          aws_access_key_id=credentials['AccessKeyId'],
                                          aws_secret_access_key=credentials['SecretAccessKey'],
                                          aws_session_token=credentials['SessionToken'],)
                kms_client = boto3.client('kms',
                                          aws_access_key_id=credentials['AccessKeyId'],
                                          aws_secret_access_key=credentials['SecretAccessKey'],
                                          aws_session_token=credentials['SessionToken'],)

            else:
                cf_client = boto3.client('cloudformation')
                ec2_client = boto3.client('ec2')
                kms_client = boto3.client('kms')

            cf_util = CloudFormationUtil(cf_client)

            if version:
                cf_params["VersionParam"] = version
            else:
                version = datetime.now().isoformat('-').replace(":", "-")

            if ami_id:
                cf_params["AMIParam"] = ami_id
            elif ami_tag_value:
                images = ec2_client.describe_images(Filters=[
                    {'Name': 'tag:ArtifactID',
                     'Values': [ ami_tag_value ]}
                ])['Images']

                if len(images) == 0:
                    raise DeployException("No images found for search '{}'".format(ami_tag_value))
                elif len(images) > 1:
                    print images
                    raise DeployException("More than 1 image found for search '{}'".format(ami_tag_value))
                else:
                    ami_id = images[0]["ImageId"]
                    # print images[0]
                    print "Located AMI {} - {} created {}".format(ami_id, images[0]['Name'], images[0]['CreationDate'])

                cf_params["AMIParam"] = ami_id

            # Then re-format the python dictionary into the boto3 format for stack parameters
            secrets = []
            for key in cf_params:

                if type(cf_params[key]) is dict:
                    raise DeployException("Objects were found with nested values, you will need to specify which set of parameters to use with \"--scope <object_name>\"".format(key))

                # check if the value contains KMS encrypted value (KMSEncrypted /KMSEncrypted tag pair)
                # if true, decrypt and replace the value
                encryption_check = re.search('KMSEncrypted(.*)/KMSEncrypted', cf_params[key])

                if encryption_check:
                    decrypted_value = kms_client.decrypt(CiphertextBlob=base64.b64decode(encryption_check.group(1)))["Plaintext"]
                    cf_params[key] = decrypted_value
                    secrets += [decrypted_value]

            try:
                with open(template_name, "r") as myfile:
                    data = myfile.read()
            except Exception as error:
                raise DeployException("Unable to locate CloudFormation template ''{}'\n{}".format(template_name, error))

            try:
                if re.match(REGEX_YAML, template_name):
                    application = yaml.load(data)
                elif re.match(REGEX_JSON, template_name):
                    application = json.load(data)
                else:
                    raise DeployException("Cloudformation template must be a JSON or YAML file")

            except Exception as error:
                raise DeployException("Unable to parse CloudFormation template '{}'\n{}".format(template_name, error))

            if application is None:
                raise DeployException("It looks like the CloudFormation template file is empty")

            parameters = []
            if 'Parameters' in application:

                for param, values in application['Parameters'].items():

                    if param in cf_params:
                        parameters += [{
                            "ParameterKey": param,
                            "ParameterValue": cf_params[param]
                            }]
                    else:
                        if create:
                            # If there is no default throw an error
                            defaultValue = values.get('Default')

                            if defaultValue is not None:
                                parameters += [{
                                    "ParameterKey": param,
                                    "ParameterValue": defaultValue
                                }]
                            else:
                                raise DeployException("Cannot CREATE new stack with missing parameter {}".format(param))
                                sys.exit(-1)
                        else:
                            print "Using current stack value for parameter {}".format(param)
                            parameters += [{
                                "ParameterKey": param,
                                "UsePreviousValue": True
                                }]

                print "Using stack parameters"
                print secure_print(json.dumps(parameters, indent=2), secrets)
            else:
                print "Specified template has no stack parameters"

            change_set_name = ""
            changeset = None

            if create:
                change_set_name = "Create-{}".format(version.replace(".", "-"))

                changeset = cf_client.create_change_set(StackName=stack_name,
                                                        TemplateBody=data,
                                                        Parameters=parameters,
                                                        Capabilities=[
                                                            'CAPABILITY_IAM',
                                                        ],
                                                        ChangeSetName=change_set_name,
                                                        ChangeSetType="CREATE"
                                                       )

            elif delete:
                if not dry_run:
                    result = cf_client.delete_stack(StackName=stack_name)
                    print result
                else:
                    print "[Dry-Run] Not deleting stack."
            else:
                change_set_name = "Update-{}".format(version.replace(".", "-"))

                changeset = cf_client.create_change_set(
                    StackName=stack_name,
                    TemplateBody=data,
                    Parameters=parameters,
                    Capabilities=[
                        'CAPABILITY_IAM',
                    ],
                    ChangeSetName=change_set_name,
                )

            if not changeset is None:
                cf_util.wait_for_change_set_to_complete(change_set_name=change_set_name,
                                                                    stack_name=stack_name,
                                                                    debug=False)

                change_set_details = cf_client.describe_change_set(ChangeSetName=change_set_name,
                                                                   StackName=stack_name)

                # import code; code.interact(local=dict(globals(), **locals()))

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

                        print "{} {}/{} ({})".format(change_mode.ljust(34), change["LogicalResourceId"], change.get("PhysicalResourceId", ""), change["ResourceType"])

                    print ""
                else:
                    print "No CloudFormation changes detected"

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
