#!/usr/bin/env python
from stacker import *
import yaml


def construct_function_ignore(loader, parameter):
    return parameter


yaml.add_constructor(u"!FindInMap", construct_function_ignore)
yaml.add_constructor(u"!Ref", construct_function_ignore)
yaml.add_constructor(u"!GetAtt", construct_function_ignore)
yaml.add_constructor(u"!Sub", construct_function_ignore)
yaml.add_constructor(u"!Join", construct_function_ignore)

if __name__ == "__main__":
    stacker.main()