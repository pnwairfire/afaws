import copy
import json

class Config(object):

    def __init__(self, user_specified_config):
        self._set_config(user_specified_config)

    DEFAULTS = {
        'iam_instance_profile': None,  # Must be supplied by user
        'per_instance_security_group_rules': [],
        'default_efs_volumes': [],
        'makefile_root_dirs': [],
        'docker_compose_yaml_root_dirs': []
   }

    def _set_config(self, user_specified_config):
        self._config = copy.deepcopy(self.DEFAULTS)
        # ignores anything that's not a recognized field
        for k in (self.DEFAULTS):
            val = user_specified_config.get(k)
            if val is not None:
                self._config[k] = val
            elif self._config[k] is None:
                # isn't defined in either defaults or user specified config
                raise ValueError("Missing required config field %s", k)
            # else, leave default value

    def __call__(self, key):
        return self._config[key]
