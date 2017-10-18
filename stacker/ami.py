__author__ = "Steve Mactaggart"

import sys
import traceback

import boto3
import botocore

from .cf_helper.utils import DeployException, STSUtil


class AMIExecutor(object):

    def __init__(self, role=None, debug=False):
        super(AMIExecutor, self).__init__()

        self.debug = debug
        self.role = role

        if self.role:
            sts = STSUtil(sts_arn=self.role, debug=debug)
            credentials = sts.authenticate_role()['Credentials']

            self.ec2_client = boto3.client('ec2',
                                           aws_access_key_id=credentials['AccessKeyId'],
                                           aws_secret_access_key=credentials['SecretAccessKey'],
                                           aws_session_token=credentials['SessionToken'])

        else:
            self.ec2_client = boto3.client('ec2')

    def execute(self, artifact_id=None, ami_id=None):

        try:
            # images = []
            search_val = None

            if artifact_id:
                search_val = artifact_id
                images = self.ec2_client.describe_images(Filters=[
                    {
                        'Name': 'tag:ArtifactID',
                        'Values': [artifact_id]
                    }])['Images']
            elif ami_id:
                search_val = ami_id
                images = self.ec2_client.describe_images(ImageIds=[ami_id])['Images']
            else:
                raise DeployException("--artifact-id or --ami-id must be supplied for the search")

            if len(images) == 0:
                raise DeployException("No images found for search '{}'".format(search_val))
            elif len(images) > 1:
                print (images)
                raise DeployException("More than 1 image found for search '{}'".format(search_val))
            else:
                ami_id = images[0]["ImageId"]
                name = images[0]['Name']
                create_date = images[0]['CreationDate']

                if self.debug:
                    print ("Located AMI '{}' - {} created {}".format(ami_id, name, create_date))
                else:
                    print (ami_id)
                    return ami_id

        except botocore.exceptions.ClientError as e:
            if str(e) == "An error occurred (ValidationError) when calling the UpdateStack operation: No updates are to be performed.":
                print ("No stack update required - CONTINUING")
            else:
                print ("Unexpected error: {}".format(e))
                sys.exit(1)
