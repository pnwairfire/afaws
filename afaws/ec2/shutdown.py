import logging

import boto3
from botocore.exceptions import ClientError

from .resources import Instance
from .network import SecurityGroupManager
from ..asyncutils import run_in_loop_executor, run_with_retries
from .execute import Ec2SshExecuter


__all__ = [
    'Ec2Shutdown',
    'AutoShutdownScheduler'
]

class FailedToShutDownError(RuntimeError):
    pass

class Ec2Shutdown(object):

    def __init__(self):
        self._client = boto3.client('ec2')

    ## Public Interface

    async def shutdown(self, instance_identifiers, terminate=False):
        instances = [await Instance(n) for n in instance_identifiers]

        instance_ids = [i.id for i in instances]

        await self._stop(instance_ids)

        if terminate:
            await run_in_loop_executor(self._client.terminate_instances,
                InstanceIds=instance_ids)

        for i in instances:
            await SecurityGroupManager.remove_instance_from_rules(i)

    STOP_RETRY_WAIT = 10
    MAX_STOP_ATTEMPTS = (60 / STOP_RETRY_WAIT) * 5 # retry for up to 5 minutes
    async def _stop(self, instance_ids):
        logging.info("Stopping instances %s", instance_ids)
        # Run with retries in order to handle the following error:
        #    botocore.exceptions.ClientError: An error occurred (IncorrectInstanceState)
        #      when calling the StopInstances operation: Instance 'i-0a28ec81c26203dd4'
        #      cannot be stopped as it has never reached the 'running' state.
        await run_with_retries(run_in_loop_executor, [self._client.stop_instances],
            {'InstanceIds': instance_ids}, FailedToShutDownError,
            exceptions_whitelist=(ClientError,)) # should be tuple


class AutoShutdownScheduler(object):

    def __init__(self, ssh_key):
        self._ssh_key = ssh_key

    async def schedule_termination(self, instances_or_identifiers,
            minutes_until_auto_shutdown):
        logging.info("Scheduling auto-shutdown in %s minutes",
            minutes_until_auto_shutdown)
        executer = Ec2SshExecuter(self._ssh_key, instances_or_identifiers)
        await executer.wait_for_ssh_connectivity()
        await executer.execute("which at || sudo apt-get install -y at")
        await executer.execute('echo "sudo halt" | at now + {} minutes'.format(
            minutes_until_auto_shutdown))
