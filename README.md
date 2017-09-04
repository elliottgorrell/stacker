# Stacker - A Cloudformation Deployment tool

## Installation

Until this package is published to a pypy server for easy install, you will need to clone this repository and install manually.

Do this with:

```
pip install .
```

Now you are ready to use the `stacker` command line tool to deliver change to your application environments.

## Testing

We use `Tox` and `PyTest` for unit testing Stacker.
PyTest is a nice testing framework that gets rid of a lot of the boilerplate code from the standard `unittesting` framework.
Tox handles packagin running the tests in different python environments. This helps make sure what you package and upload actually both
installs correctly and is supported by all the environments we claim.

Simply run `tox` inside the project.
This will create virtual environments for each python environment listed in `tox.ini`
Tox will then package up the application and run any tests found for PyTest in each environment.
Tests are discovered using standard PyTest standards such as the `test_` prefix on a filename.




## Usage

Stacker currently supports 2 primary functions:

* Deploying CloudFormation stacks
* Searching for AMI's

The tool has been modelled on the `awscli`, where the primary `stacker` command has sub commands for each action.

```
$ stacker --help
usage: stacker [-h] [--debug] [--role ROLE] {deploy,ami} ...

positional arguments:
  {deploy,ami}
    deploy      Deploy the specified version to the environment.
    ami         Utilities for AWS AMI management.


optional arguments:
  -h, --help    Show this help message and exit
  --debug, -d   Show debug log messages
  --role        The AWS IAM Role to assume.
```

### Using common settings

Common settings, such as specifying an AWS IAM Role to assume need to be supplied before the sub-command.

For example:

```
$ stacker --role arn:aws:iam::12345:role/somerole deploy
```

### Using the deploy sub command

To manage CloudFormation stacks with `stacker` you need to use the `deploy` sub-command.

```
$ stacker deploy --help
usage: stacker deploy [-h] [--debug] --stack_name STACK_NAME [--create]

                    [--delete] [--config_filename CONFIG_FILENAME] --template
                    TEMPLATE [--ami_id AMI_ID] [--ami_tag_value AMI_TAG_VALUE]
                    [--scope SCOPE] [--dry_run]
                    [--add_parameters PARAMETER1=VALUE1 PARAMETER2=VALUE2... ]
                    [--version VERSION]

optional arguments:
  -h, --help            Show this help message and exit
  --debug, -d           Show debug log messages
  --name                The name of the stack to update. yay
  --create, -c          Use flag to create new stack vs performing update.
  --delete, -D          Use flag to delete an existing stack.
  --config-filename     The name of file to load the config parameters from
  --template -t         The name of the CloudFormation template to apply.
  --ami-id              The explicit AMI id to use for deployment
  --ami-tag-value       The tag value of the AMI to search for
  --scope -s            The scope for the config parameters
  --dry-run             Produces a changeset for stack however does not update
  --add-parameters      Used to supply additional parameters not in the config
                            file. Needs to be in the format "key=value"
  --version VERSION     The build number of this deployment
```

### Using the ami sub command

To manage AMI lookups with `stacker` you need to use the `ami` sub-command.

```
$ stacker ami --help
usage: stacker ami [-h] [--debug] [--ami_id AMI_ID] [--artifact_id ARTIFACT_ID]

optional arguments:
  -h, --help            show this help message and exit
  --debug, -d           Show debug log messages
  --ami-id              The AMI ID to search for (used to test across account
                        permissions)
  --artifact-id         The tag value of the AMI to search for
```
