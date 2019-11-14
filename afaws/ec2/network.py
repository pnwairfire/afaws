"""Module for managing network security groups, etc.

TODO:
 - support IPv6 ?
"""
import logging

import boto3

from .resources import SecurityGroup, Instance
from ..asyncutils import run_in_loop_executor

class SecurityGroupManager(object):

    def __init__(self, sg_identifier):
        self._ec2 = boto3.resource('ec2')
        self._sg_identifier = sg_identifier
        self._security_group = None


    async def security_group(self):
        if not self._security_group:
            sg = await SecurityGroup(self._sg_identifier)
            self._security_group = await run_in_loop_executor(
                self._ec2.SecurityGroup, sg.id)
        return self._security_group

    async def add_rule(self, is_inbound, protocol, from_port, to_port,
            instance_or_identifier):
        sg = await self.security_group()
        logging.info("Adding %sbound %s %s:%s from %s to %s (%s)",
            'in' if is_inbound else 'out', protocol, from_port, to_port,
            instance_or_identifier, sg.group_name, sg.id)

        i = await Instance(instance_or_identifier)

        func_name = 'authorize_{}gress'.format('in' if is_inbound else 'e')
        func = getattr(sg, func_name)
        func(
            GroupId=sg.id,
            IpPermissions=[{
                'IpProtocol': protocol,
                'FromPort': from_port,
                'ToPort': to_port,
                'IpRanges': [{
                    'CidrIp': '{}/32'.format(i.classic_address.public_ip),
                    'Description': i.name
                }]
            }]
        )

    async def add_inbound_rule(self, protocol, from_port, to_port, instance_or_identifier):
        """Convenience method for add_rule(True, ...)
        """
        await self.add_rule(True, protocol, from_port, to_port, instance_or_identifier)

    async def add_outbound_rule(self, protocol, from_port, to_port, instance_or_identifier):
        """Convenience method for add_rule(False, ...)
        """
        await self.add_rule(False, protocol, from_port, to_port, instance_or_identifier)

    async def remove_rule(self, is_inbound, protocol, from_port, to_port, cidr_ip):
        sg = await self.security_group()
        logging.info("Removing %sbound auth - %s %s %s:%s %s (%s)",
            'in' if is_inbound else 'out', cidr_ip, protocol, from_port,
            to_port, sg.group_name, sg.id)

        func_name = 'revoke_{}gress'.format('in' if is_inbound else 'e')
        func = getattr(sg, func_name)
        func(
            GroupId=sg.id,
            IpPermissions=[
                {
                    'FromPort': from_port,
                    'IpProtocol': protocol,
                    'IpRanges': [{
                        'CidrIp': cidr_ip,
                    }],
                    'ToPort': to_port
                }
            ]
        )

    @classmethod
    async def remove_instance_from_rules(cls, instance_or_identifier):
        logging.info("Removing instance %s from any security group rules",
            instance_or_identifier)
        i = await Instance(instance_or_identifier)
        cidr_ip = '{}/32'.format(i.classic_address.public_ip)
        ec2_client = boto3.client('ec2')
        resp = await run_in_loop_executor(ec2_client.describe_security_groups)

        for sg in resp.get('SecurityGroups', []):
            sg_manager = cls(sg['GroupId'])
            for ip_perm in sg['IpPermissions']:
                for ip_range in ip_perm.get('IpRanges',[]):
                    if ip_range['CidrIp'] == cidr_ip:
                        await sg_manager.remove_rule(True, ip_perm['IpProtocol'],
                            ip_perm['FromPort'], ip_perm['ToPort'], cidr_ip)

            for ip_perm in sg['IpPermissionsEgress']:
                for ip_range in ip_perm.get('IpRanges',[]):
                    if ip_range['CidrIp'] == cidr_ip:
                        await sg_manager.remove_rule(False, ip_perm['IpProtocol'],
                            ip_perm['FromPort'], ip_perm['ToPort'], cidr_ip)
