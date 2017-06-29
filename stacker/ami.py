__author__ = "Steve Mactaggart"

import sys
import traceback

import boto3
import botocore

from cf_helper.utils import DeployException, STSUtil


class AMIExecutor(object):

    def execute(self, role, artifact_id, ami_id, debug=False):

        try:
            if role:
                sts = STSUtil(sts_arn=role, debug=debug)
                credentials = sts.authenticate_role()['Credentials']

                ec2_client = boto3.client('ec2',
                                         aws_access_key_id = credentials['AccessKeyId'],
                                         aws_secret_access_key = credentials['SecretAccessKey'],
                                         aws_session_token = credentials['SessionToken'],)

            else:
                ec2_client = boto3.client('ec2')

            images = []
            search_val = "unknown"

            if artifact_id:
                search_val = artifact_id
                images = ec2_client.describe_images(Filters=[
                    {'Name': 'tag:ArtifactID',
                     'Values': [artifact_id]}
                ])['Images']
            elif ami_id:
                search_val = ami_id
                images = ec2_client.describe_images(ImageIds=[ami_id])['Images']
            else:
                raise DeployException("--artifact-id or --ami-id must be supplied for the search")

            if len(images) == 0:
                raise DeployException("No images found for search '{}'".format(search_val))
            elif len(images) > 1:
                print images
                raise DeployException("More than 1 image found for search '{}'".format(search_val))
            else:
                ami_id = images[0]["ImageId"]

                if debug:
                    print "Located AMI '{}' - {} created {}".format(ami_id, images[0]['Name'], images[0]['CreationDate'])
                else:
                    print ami_id

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
