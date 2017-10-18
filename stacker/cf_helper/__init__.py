import yaml

def secure_print(plaintext, secrets):

    result = plaintext

    for secret in secrets:
        result = result.replace(secret, "*****")

    return result