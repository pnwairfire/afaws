import asyncio
import logging

import boto3

from .resources import Instance

__all__ = [
    'Ec2Reboot'
]

class Ec2Reboot(object):

    def __init__(self):
        self._client = boto3.client('ec2')

    ## Public Interface

    async def reboot(self, instance_identifiers):
        instances = [await Instance(n) for n in instance_identifiers]

        instance_ids = [i.id for i in instances]
        self._client.reboot_instances(InstanceIds=instance_ids, DryRun=False)

        await asyncio.gather(*[
            Instance.wait_until_running(instance) for instance in instances
        ])

        return instances
