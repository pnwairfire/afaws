import datetime
import logging
import sys

import boto3
from botocore.exceptions import ClientError, WaiterError
from .exceptions import PostLaunchFailure
from .resources import SecurityGroup, Image, Instance
from .network import SecurityGroupManager
from ..asyncutils import run_in_loop_executor

__all__ = [
    'Ec2Launcher',
    'Ec2CloneLauncher'
]


##
## Launchers
##

class Ec2Launcher(object):

    def __init__(self, image_identifier, config, **options):
        self._config = config
        self._client = boto3.client('ec2')
        self._ec2 = boto3.resource('ec2')
        self._identifier = image_identifier
        self._set_and_validate_options(options)

    ## Public Interface

    async def launch(self, new_instance_names):
        await self._set_new_instance_fields_from_options()
        self._image = await self._get_image()
        self._ensure_new_instance_fields_set()
        await self._validate_new_instance_names(new_instance_names)
        instances = await self._create_instances()
        try:
            await self._associate_iam_instance_profile(instances)
            await self._post_launch_tasks(instances)
        except Exception as e:
            logging.error("Failure in post-launch tasks: %s", e)
            raise PostLaunchFailure(e, instances)

        return instances


    ## Options and Validation

    def _set_and_validate_options(self, options):
        self._options = options
        # TODO: anything to check?

    async def _set_new_instance_fields_from_options(self):
        self._instance_type = self._options.get('instance_type')
        # TODO: if defined, make sure it's a valid type

        self._key_pair_name = self._options.get('key_pair_name')

        self._security_group_ids = [(await SecurityGroup(g)).id
            for g in self._options.get('security_groups', [])]

        self._volumes = []
        if self._options.get('ebs_volume_size'):
            self._volumes = [{
                'device_name': self._options.get('ebs_device_name'),
                'size': self._options['ebs_volume_size']
            }]

        self._instance_initiated_shutdown_behavior = self._options.get(
            'instance_initiated_shutdown_behavior') or 'stop'
        if self._instance_initiated_shutdown_behavior not in ('stop', 'terminate'):
            raise RuntimeError("'instance_initiated_shutdown_behavior' must "
                "be 'stop' or 'terminate', if set")

        # if not self._options.get('subnet'):
        #     raise RuntimeError("'subnet' must be defined")
        # self._subnet = self._ec2.Subnet(options['subnet'])
        # TODO: make subnet exists

    def _ensure_new_instance_fields_set(self):
        # TODO: for those not specified, prompt or just fail ?
        if not self._instance_type:
            raise RuntimeError("Specify instance type")

        if not self._key_pair_name:
            raise RuntimeError("Specify key pair name")

        if not self._security_group_ids:
            raise RuntimeError("Specify security group(s)")

        if not self._volumes:
            raise RuntimeError("Specify security ebs volume size")

    async def _validate_new_instance_names(self, new_instance_names):
        if len(new_instance_names) == 0:
            raise RuntimeError("Specify at least one new instance")

        if len(new_instance_names) != len(set(new_instance_names)):
            raise RuntimeError("New instance names must be unique")


        kwargs = dict(Filters=[{'Name': 'tag:Name', 'Values': new_instance_names}])
        existing_instances = [i.name for i in await Instance.find(**kwargs)]
        if len(existing_instances) > 0:
            raise RuntimeError("The following instances already exist: "
                "{}".format(', '.join(existing_instances)))

        self._new_instance_names = new_instance_names


    ## New Instances

    async def _get_image(self):
        """Defined as function so that Ec2CloneLauncher can override it
        """
        return await Image(self._identifier)

    async def _create_instances(self):
        # see https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.ServiceResource.create_instances
        num_new_instance_names = len(self._new_instance_names)

        block_device_mappings = []
        for v in self._volumes:
            block_device_mappings.append({
                'DeviceName': v['device_name'],
                'Ebs': {
                    # 'DeleteOnTermination': True|False,
                    # 'Iops': 123,
                    # 'SnapshotId': 'string',
                    'VolumeSize': v['size'],
                    # 'VolumeType': 'standard'|'io1'|'gp2'|'sc1'|'st1',
                    # 'Encrypted': True|False,
                    # 'KmsKeyId': 'string'
                },
                # 'NoDevice': 'string'
            })

        kwargs = {
            "ImageId": self._image.id,
            "InstanceType": self._instance_type,
            "KeyName": self._key_pair_name,
            "MinCount": num_new_instance_names,
            "MaxCount": num_new_instance_names,
            "SecurityGroupIds": self._security_group_ids,
            "BlockDeviceMappings": block_device_mappings,
            "InstanceInitiatedShutdownBehavior": self._instance_initiated_shutdown_behavior,
            # TODO: can we name it here rather than create tag below ?
            # KeyName='mykeyname',
        }

        # TODO: launch with specific public ssh key

        logging.info("Creating %s instances", num_new_instance_names)
        logging.info("  InstanceType: %s", self._instance_type)
        logging.info("  KeyName: %s", self._key_pair_name)
        logging.info("  SecurityGroupIds: %s", self._security_group_ids)
        logging.info("  EBS size(s):  %s", ', '.join([str(d['Ebs']['VolumeSize'])
            for d in block_device_mappings]))
        logging.info("  InstanceInitiatedShutdownBehavior: %s",
            self._instance_initiated_shutdown_behavior)
        instances = await Instance.create_multiple(self._new_instance_names,
            tags=self._options.get('tags', {}), **kwargs)
        # at this point, they must all be running

        logging.info("%s instances running", len(instances))
        return instances

    ## Post Launch

    async def _associate_iam_instance_profile(self, instances):

        for instance in instances:
            logging.info("  %s - %s", instance.name,
                instance.classic_address.public_ip
                if instance.classic_address else '?')
            await run_in_loop_executor(
                self._client.associate_iam_instance_profile,
                IamInstanceProfile=self._config('iam_instance_profile'),
                InstanceId = instance.id
            )

    async def _add_instances_to_security_groups(self, instances):
        for rule_args in self._config('per_instance_security_group_rules'):
            sg_manager = SecurityGroupManager(rule_args[0])
            for i in instances:
                args = rule_args[1:] + [i.id]
                await sg_manager.add_rule(*args)


    async def _post_launch_tasks(self, instances):
        # TODO: update DNS? (or at least output new ip addresses (With subdomain for each)
        # TODO: anything else
        await self._add_instances_to_security_groups(instances)


class Ec2CloneLauncher(Ec2Launcher):
    """Functions like Ec2Launcher, except that an image is
    """

    async def _get_image(self):
        """Overrides Ec2Launcher._get_image to first create image from instance
        and then instantiated an image obkect from

        """
        instance = await Instance(self._identifier)
        await self._set_new_instance_fields_from_instance(instance)
        return await self._create_image(instance)


    ## Get Existing Instance to clone

    async def _set_new_instance_fields_from_instance(self, instance):
        """Only sets fields that weren't set in options
        """
        # if not self._subnet:
        #     self._subnet = self.instance.subnet

        if not self._instance_type:
            self._instance_type = instance.instance_type

        if not self._key_pair_name:
            self._key_pair_name = instance.key_name

        if not self._security_group_ids:
            self._security_group_ids = [
                e['GroupId'] for e in instance.security_groups]

        if not self._volumes:
            self._volumes = [{
                'device_name': d['DeviceName'],
                'size': (await run_in_loop_executor(self._ec2.Volume,
                    d['Ebs']['VolumeId'])).size
            } for d in instance.block_device_mappings]

    ## Creating new image

    async def _create_image(self, instance):
        name_desc = '-'.join([instance.name, instance.id,
            datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')])
        logging.info("Creating image %s", name_desc)
        image = instance.create_image(
            Description=name_desc,
            DryRun=False,
            Name=name_desc,
            NoReboot=True
        )

        logging.info("Waiting for image %s (%s)", image.id, name_desc)
        while True:
            try:
                image.wait_until_exists('self',
                    Filters=[{'Name':'state','Values':['available']}])
                break
            except WaiterError as e:
                logging.info(
                    "Boto gave up waiting for image %s (%s). Trying again",
                    image.id, name_desc)


        logging.info("Image %s (%s) is available", image.id, name_desc)
        return image


    ## Post Launch

    async def _post_launch_tasks(self, instances):
        await super()._post_launch_tasks(instances)
        await run_in_loop_executor(
            self._client.deregister_image,
            ImageId=self._image.id
        )
