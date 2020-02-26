import logging

import boto3

from .resources import Instance
from .network import SecurityGroupManager
from ..asyncutils import run_in_loop_executor
from .execute import Ec2SshExecuter


__all__ = [
    'Ec2Shutdown',
    'AutoShutdownScheduler'
]

class Ec2Shutdown(object):

    def __init__(self):
        self._client = boto3.client('ec2')

    ## Public Interface

    async def shutdown(self, instance_identifiers, terminate=False):
        instances = [await Instance(n) for n in instance_identifiers]

        instance_ids = [i.id for i in instances]
        await run_in_loop_executor(self._client.stop_instances,
            InstanceIds=instance_ids)
        if terminate:
            await run_in_loop_executor(self._client.terminate_instances,
                InstanceIds=instance_ids)

        for i in instances:
            await SecurityGroupManager.remove_instance_from_rules(i)

class AutoShutdownScheduler(object):

    def __init__(self, ssh_key):
        self._ssh_key = ssh_key

    async def schedule_termination(self, instances_or_identifiers,
            minutes_until_auto_shutdown):
        logging.info("Scheduling auto-shutdown in %s minutes",
            minutes_until_auto_shutdown)
        executer = Ec2SshExecuter(self._ssh_key, instances_or_identifiers)
        await executer.execute("which at || sudo apt-get install -y at")
        await executer.execute('echo "sudo halt" | at now + {} minutes'.format(
            minutes_until_auto_shutdown))
