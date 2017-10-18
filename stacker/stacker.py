from cf_helper.utils import DeployException

__author__ = 'steve.mactaggart & elliott.gorrell'

import argparse
import os
import sys, traceback

import pkg_resources  # part of setuptools

from deploy import DeployExecutor
from ami import AMIExecutor

def build_deploy_parser(parser):

    parser.add_argument('--debug', '-d',
                        default=False,
                        help='Show debug log messages',
                        action="store_true")
    parser.add_argument('--name',
                        required=True,
                        help='The name of the stack to update.')
    parser.add_argument('--create', '-c',
                        help='Use flag to create new stack vs performing update.',
                        default=False,
                        action='store_true')
    parser.add_argument('--delete', '-D',
                        help='Use flag to delete an existing stack.',
                        default=False,
                        action='store_true')
    parser.add_argument('--config',
                        help="The path of the file to load the config parameters from",
                        required=False)
    parser.add_argument('--template', '-t',
                        required=True,
                        help='The name of the CloudFormation template to use.')
    parser.add_argument('--ami-id',
                        help="The explicit AMI id to use for deployment",
                        required=False)
    parser.add_argument('--ami-tag',
                        help="The tag value of the AMI to search for",
                        required=False)
    parser.add_argument('--scope',
                        help="The scope for the config parameters",
                        required=False)
    parser.add_argument('--dry-run',
                        help="Produces a changeset for stack however does not update",
                        required=False,
                        default=False,
                        action='store_true')
    parser.add_argument('--add-parameters',
                        help='Used to supply additional parameters not in the config file. Needs to be in the format "key=value"',
                        nargs='*',
                        required=False)
    parser.add_argument('--version','-v',
                        help="The build number of this deployment",
                        required=False)

    parser.set_defaults(func=execute_deploy)


def execute_deploy(args):

    executor = DeployExecutor(role=args.role,debug=args.debug)
    executor.execute(stack_name=args.name,
                     config_filename=args.config,
                     template_name=args.template,
                     add_parameters=args.add_parameters,
                     version=args.version,
                     ami_id=args.ami_id,
                     ami_tag_value=args.ami_tag,
                     scope=args.scope,
                     create=args.create,
                     delete=args.delete,
                     dry_run=args.dry_run)


def build_ami_parser(parser):

    parser.add_argument('--debug', '-d',
                        default=False,
                        help='Show debug log messages',
                        action="store_true")
    parser.add_argument('--ami-id',
                        help="The AMI ID to search for (used to test across account permissions)",
                        required=False)
    parser.add_argument('--artifact-id',
                        help="The tag value of the AMI to search for",
                        required=False)

    parser.set_defaults(func=execute_ami)


def execute_ami(args):

    executor = AMIExecutor(role=args.role)

    try:
        executor.execute(ami_id=args.ami_id,
                         artifact_id=args.artifact_id)
    except DeployException as error:
        print "ERROR: {0}".format(error)
    except Exception as error:
        traceback.print_exc(file=sys.stdout)
        traceback.print_stack(file=sys.stdout)
        print "ERROR: {0}".format(error)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)


def main(argv=None):

    # Python filesystem hack required to enable stream flushing on demand
    sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)

    try:
        # create the top-level parser
        parser = argparse.ArgumentParser(prog='stacker', description="A set of utilities for Deploying Cloudformation Stacks")
        parser.add_argument('--debug', '-d', default=False, help='Show debug log messages', action="store_true")
        parser.add_argument('--role', help='The AWS IAM Role to assume.')
        parser.add_argument('--version','-v', help="Prints the version", dest="show_version", action="version", version=pkg_resources.require("Stacker")[0].version)

        subparsers = parser.add_subparsers()

        parser_deploy = subparsers.add_parser('deploy', help='Deploy or update a Cloudformation stack')
        build_deploy_parser(parser_deploy)

        parser_ami = subparsers.add_parser('ami', help='Utilities for AWS AMI management.')
        build_ami_parser(parser_ami)

        args = parser.parse_args(argv)
        args.func(args)

    except Exception as error:
        traceback.print_exc(file=sys.stdout)
        traceback.print_stack(file=sys.stdout)
        print "ERROR: {0}".format(error)
        traceback.print_exc(file=sys.stdout)
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
