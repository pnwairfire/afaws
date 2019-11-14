# For application load balancer, see:
#   https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elbv2.html
# Classic load balancer docs are:
#  https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/elb.html

import logging
import sys

import boto3

from .resources import Instance
from ..asyncutils import run_in_loop_executor

class PoolDoesNotExistError(RuntimeError):
    pass

class ElbPool(object):

    def __init__(self, arn, name=None, client=None):
        """
        Note that name is nice to have to reference later by client,
        but not required.
        """
        self._client = client or boto3.client('elbv2')
        self.arn = arn
        self.name = name
        self._target_groups = None

    async def load(self, force_reload=False):
        if self._target_groups is None or force_reload:
            await self._load_target_groups()
            await self._load_instances()

    async def _load_target_groups(self):
        resp = await run_in_loop_executor(
            self._client.describe_target_groups,
            LoadBalancerArn=self.arn
        )
        if not resp or not resp.get('TargetGroups'):
            raise RuntimeError("No target groups")
        self._target_groups = resp['TargetGroups']
        self._target_groups.sort(key=lambda tg: tg['TargetGroupName'])

    async def _load_instances(self):
        for tg in self._target_groups:
            r = await run_in_loop_executor(
                self._client.describe_target_health,
                TargetGroupArn=tg['TargetGroupArn']
            )
            if r and r.get('TargetHealthDescriptions'):
                tg['instances'] = r['TargetHealthDescriptions']
                for i in tg['instances']:
                    i['object'] = await Instance(i['Target']['Id'])
                tg['instances'].sort(key=lambda i: i['object'].name)
            else:
                logging.warn("Target group %s has no targets (instances)",
                    tg['TargetGroupArn'])
                tg['instances'] = []

    @property
    def target_groups(self):
        return self._target_groups or []

    async def add(self, instance_identifiers):
        instances = [await Instance(n) for n in instance_identifiers]
        await self.load()
        for tg in self.target_groups:
            targets = [{'Id': i.id} for i in instances]
            r = await run_in_loop_executor(
                self._client.register_targets,
                TargetGroupArn=tg['TargetGroupArn'],
                Targets=targets
            )
        await self.load(force_reload=True)

    async def remove(self, instance_identifiers):
        instances = [await Instance(n) for n in instance_identifiers]
        await self.load()
        for tg in self.target_groups:
            #targets = [{'Id': i.id, 'Port': tg['Port'], 'AvailabilityZone': 'all'} for i in instances]
            targets = [{'Id': i.id} for i in instances]
            r = await run_in_loop_executor(
                self._client.deregister_targets,
                TargetGroupArn=tg['TargetGroupArn'],
                Targets=targets
            )
        await self.load(force_reload=True)

    @classmethod
    async def from_name(cls, pool_name):
        client = boto3.client('elbv2')
        try:
            resp = await run_in_loop_executor(
                client.describe_load_balancers, Names=[pool_name])

        except client.exceptions.LoadBalancerNotFoundException:
            raise PoolDoesNotExistError("ELB pool does not exist")

        if not resp or not resp.get('LoadBalancers'):
            raise PoolDoesNotExistError("No matching ELB pools")

        elif len(resp['LoadBalancers']) > 1:
            raise RuntimeError("More than one matching ELB pool")

        pool = ElbPool(resp['LoadBalancers'][0]['LoadBalancerArn'],
            name=resp['LoadBalancers'][0]['LoadBalancerName'], client=client)
        await pool.load()
        return pool

    @classmethod
    async def all(cls):
        client = boto3.client('elbv2')
        resp = await run_in_loop_executor(client.describe_load_balancers)
        pools = []
        for lb in resp['LoadBalancers']:
            # TODO:  if thread safe, pass in client
            pools.append(ElbPool(lb['LoadBalancerArn'], name=lb['LoadBalancerName']))
            await pools[-1].load()
        return pools