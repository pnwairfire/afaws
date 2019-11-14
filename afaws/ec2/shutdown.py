import boto3

from .resources import Instance
from .network import SecurityGroupManager
from ..asyncutils import run_in_loop_executor

__all__ = [
    'Ec2Shutdown'
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
