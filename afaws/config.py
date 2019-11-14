import json

class Config(object):

    def __init__(self, user_specified_config):
        self._set_config(user_specified_config)

    REQUIRED_CONFIG_FIELDS = (
        'iam_instance_profile', 'per_instance_security_group_rules',
        'default_efs_volumes', 'makefile_root_dirs',
        'docker_compose_yaml_root_dirs'
    )

    def _set_config(self, user_specified_config):
        self._config = {}
        # ignores anything that's not a required field
        for k in (self.REQUIRED_CONFIG_FIELDS):
            val = user_specified_config.get(k)
            if not val:
                raise ValueError("Missing required config field %s", k)
            self._config[k] = val

    def __call__(self, key):
        return self._config[key]
