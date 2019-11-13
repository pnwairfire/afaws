import abc
import logging
import sys
import traceback

import afscripting

__all__ = [
    'exit_with_msg',
    'AwsScriptArgs'
]

def exit_with_msg(msg):
    logging.info(traceback.format_exc())
    logging.error(msg)
    sys.exit(1)

class AwsScriptArgs(abc.ABC):

    REQUIRED_ARGS = []
    OPTIONAL_ARGS = []
    EXAMPLE_STRING = ""

    def __init__(self):
        _, self.args = afscripting.args.parse_args(self.REQUIRED_ARGS,
            self.OPTIONAL_ARGS, epilog=self.EXAMPLE_STRING)
        self._check_args()

    def _check_args(self):
        # Override in derived classes
        pass
