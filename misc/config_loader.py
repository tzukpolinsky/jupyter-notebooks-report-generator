import json


def load_config(config_path: str):
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config
