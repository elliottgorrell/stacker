import time
import boto3
import getpass
import logging

class DeployException(Exception):
    pass

class STSUtil(object):

    def __init__(self, sts_arn):
        self.sts_arn = sts_arn

    def authenticate_role(self):
        sts_client = boto3.client("sts")

        current_user = getpass.getuser()
        assuming_user = "deploy@"+current_user
        logging.info("Assuming role of {} as {}".format(self.sts_arn, assuming_user))
        self.role = sts_client.assume_role(RoleArn=self.sts_arn,
                                           RoleSessionName=assuming_user)

        return self.role

class CloudFormationUtil(object):

    def __init__(self, cf_client):
        self.cf_client = cf_client

    def has_parameter(self, parameter_set, paramater_name):

        for param in parameter_set:
            if param['ParameterKey'] == paramater_name:
                return True
        return False

    def wait_for_change_set_to_complete(self, stack_name, change_set_name, loop_timeout=1, max_loops=30):

        still_checking = True
        loop_count = 1

        stack = None
        while still_checking:

            stack = self.cf_client.describe_change_set(
                ChangeSetName=change_set_name,
                StackName=stack_name,
                )

            state = stack['Status']

            logging.info("({}/{}) - ChangeSet [{}] for {} is {}".format(loop_count, max_loops, change_set_name, stack_name, state))

            if "IN_PROGRESS" in state or "PENDING" in state:
                still_checking = True
            elif "FAILED" in state or "UPDATE_ROLLBACK_COMPLETE" == state:
                raise DeployException("Stack '{}' ChangeSet failed, "
                                      "last status was '{}' - {}".format(stack_name, state, stack["StatusReason"]))
            else:
                still_checking = False

            if still_checking:
                if loop_count+1 > max_loops:
                    raise DeployException("Timeout waiting for stack '{}' to complete modification, "
                                          "last status was '{}'".format(stack_name, state))
                loop_count += 1

                time.sleep(loop_timeout)

    def wait_for_deploy_to_complete(self, stack_name, show_outputs=True, loop_timeout=15, max_loops=300):

        still_checking = True

        loop_count = 1

        stack = None
        while still_checking:

            stack = self.cf_client.describe_stacks(StackName=stack_name)['Stacks'][0]
            state = stack['StackStatus']

            print "({}/{}) - {} is {}".format(loop_count, max_loops, stack_name, state)
            if "IN_PROGRESS" in state:
                still_checking = True
            elif "FAILED" in state or "UPDATE_ROLLBACK_COMPLETE" == state:
                raise DeployException("Stack '{}' modification failed, "
                                      "last status was '{}'".format(stack_name, state))
            else:
                still_checking = False

            if still_checking:
                if loop_count+1 > max_loops:
                    raise DeployException("Timeout waiting for stack '{}' to complete modification, "
                                          "last status was '{}'".format(stack_name, state))
                loop_count += 1

                time.sleep(loop_timeout)

        if show_outputs and 'Outputs' in stack:
            print ""
            print "Stack Outputs"
            print "-------------"
            for output in stack['Outputs']:
                print "  {}: {}".format(output['OutputKey'], output['OutputValue'])
            print ""
            print ""
