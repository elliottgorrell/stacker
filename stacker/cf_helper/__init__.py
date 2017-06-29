import yaml

def secure_print(plaintext, secrets):

    result = plaintext

    for secret in secrets:
        result = result.replace(secret, "*****")

    return result

def construct_function_ignore(loader, parameter):
    return parameter

yaml.add_constructor(u"!FindInMap", construct_function_ignore)
yaml.add_constructor(u"!Ref", construct_function_ignore)
yaml.add_constructor(u"!GetAtt", construct_function_ignore)
yaml.add_constructor(u"!Sub", construct_function_ignore)
yaml.add_constructor(u"!Join", construct_function_ignore)
