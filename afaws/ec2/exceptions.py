__all__ = [
    'PostLaunchFailure'
]

class PostLaunchFailure(Exception):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._msg = str(args[0])
        self._instances = args[1]

    @property
    def instances(self):
        return self._instances
