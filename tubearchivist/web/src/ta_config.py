"""read out config file"""

import json


def get_config():
    """ read config file """
    config_path = "config.json"

    with open(config_path, "r", encoding="utf-8") as config_file:
        data = config_file.read()

    config = json.loads(data)

    return config
