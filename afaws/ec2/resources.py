import abc
import asyncio
import logging

import boto3
import tornado.gen
from botocore.exceptions import ClientError

from ..asyncutils import run_in_loop_executor, run_with_retries

__all__ = [
    'ResourceDoesNotExistError',
    'SecurityGroup',
    'Image',
    'Instance'
]

class ResourceDoesNotExistError(Exception):
    pass

class FailedToGetIpAddress(RuntimeError):
    pass

class Ec2Resource(abc.ABC):

    async def __new__(cls, identifier):
        return cls._with_name(await cls._find_one(identifier))

    @classmethod
    def _with_names(cls, objs):
        return [cls._with_name(obj) for obj in objs]

    @classmethod
    def _with_name(cls, obj):
        setattr(obj, 'name', cls.name_from_object(obj))
        return obj

    @classmethod
    async def _find_one(cls, identifier):
        if isinstance(identifier, boto3.resources.base.ServiceResource):
            # already is a resource object
            return identifier

        # try finding image with given id
        try:
            kwargs = {cls._id_field: [identifier]}
            objs = list(await run_in_loop_executor(
                cls._collection_manager.filter, **kwargs))
            if objs:
                logging.info("Found %s with id %s", cls.__name__, identifier)
                return objs[0]
        except ClientError:
            pass
        logging.info("No %s with id: %s", cls.__name__, identifier)

        # try finding image with given name
        try:
            name_kwargs = cls._name_kwargs(identifier)
            objs = list(await run_in_loop_executor(
                cls._collection_manager.filter, **name_kwargs))
            if objs:
                if len(objs) > 1:
                    raise ResourceDoesNotExistError("More than one {} with "
                        "name '{}'".format(cls.__name__, identifier))
                logging.info("Found %s with name %s", cls.__name__, identifier)
                return objs[0]
        except ClientError:
            pass

        raise ResourceDoesNotExistError("No {} identified by '{}'".format(
            cls.__name__, identifier))

    @classmethod
    async def _all(cls):
        # todo: use cls._collection_mananger.all?
        return [e for e in await run_in_loop_executor(
            cls._collection_manager.filter)]


    @classmethod
    async def all(cls):
        return cls._with_names(await cls._all())

    @classmethod
    async def find(cls, **kwargs):
        return cls._with_names([e for e in await run_in_loop_executor(
            cls._collection_manager.filter, **kwargs)])

    @classmethod
    def name_from_object(cls, obj):
        if obj.tags:
            for t in obj.tags:
                if t['Key'] == 'Name':
                    return t['Value']
        # else returns None


class SecurityGroup(Ec2Resource):

    _collection_manager = boto3.resource('ec2').security_groups
    _id_field = 'GroupIds'

    @classmethod
    def _name_kwargs(cls, identifier):
        return {
            "GroupNames": [identifier]
        }

    @classmethod
    def name_from_object(cls, obj):
        return obj.group_name


class Image(Ec2Resource):

    _collection_manager = boto3.resource('ec2').images
    _id_field = 'ImageIds'

    @classmethod
    def _name_kwargs(cls, identifier):
        return {
            "Filters": [{'Name': 'name', 'Values': [identifier]}]
        }

    @classmethod
    def name_from_object(cls, obj):
        return obj.name

    @classmethod
    def _with_name(cls, obj):
        # obj.name is already defined; just return object
        return obj

    @classmethod
    async def all(cls):
        """Overrides base class 'all'

        base class 'all' hangs, maybe because it's retrieving *all*
        public AMIs. ('Owners' is not an allowed kwarg in 'all', but maybe
        there's a nother way to specify owner. not sure if it can be passed
        into 'find'.)
        """
        # Need to specify Owners=['self'] to avoid retrieving all public AMIs
        response = await run_in_loop_executor(
            boto3.client('ec2').describe_images, Owners=['self'])
        return [await cls(i['ImageId']) for i in response['Images']]


class Instance(Ec2Resource):

    _collection_manager = boto3.resource('ec2').instances
    _id_field = 'InstanceIds'

    @classmethod
    def _name_kwargs(cls, identifier):
        return {
            "Filters": [{'Name': 'tag:Name', 'Values': [identifier]}]
        }

    @classmethod
    async def find_all_by_name(cls, identifier):
        # Note: This doesn't seem to work for finding security groups or
        # images by name pattern (e.g. launch-wizard-*), but it does for
        # instances (e.g. web-*)
        try:
            return await cls.find(**cls._name_kwargs(identifier))
        except ClientError:
            return []

    @classmethod
    async def create_multiple(cls, new_instance_names, tags={}, **kwargs):
        # These instances won't have names yet
        instances = await run_in_loop_executor(
            boto3.resource('ec2').create_instances, **kwargs)
        await asyncio.gather(*[
            cls._wait_to_name(instance, new_instance_names[i], tags)
                for i, instance in enumerate(instances)
        ])
        instances = cls._with_names(instances)
        await asyncio.gather(*[
            cls.wait_until_running(instance) for instance in instances
        ])
        await asyncio.gather(*[
            cls.wait_for_ip_address(instance) for instance in instances
        ])

        return instances

    @classmethod
    async def _wait_to_name(cls, instance, name, tags):
        logging.info("Waiting until instance %s exists", instance.id)
        await run_in_loop_executor(instance.wait_until_exists)
        logging.info("Naming instance %s %s", instance.id, name)
        instance_tags = [{'Key': 'Name','Value': name}]
        for k,v in tags.items():
            instance_tags.append({'Key': k,'Value': v})
        # For some reason, we sometimes still get 'not exists' error,
        # so, just wait and retry
        await run_with_retries(instance.create_tags, [],
            {'DryRun': False, 'Tags': instance_tags}, False,
            RuntimeError, log_msg_prefix="Naming instance")

    @classmethod
    async def wait_until_running(cls, instance):
        logging.info("Waiting until instance %s (%s) is running",
            instance.id, instance.name)
        await run_in_loop_executor(instance.wait_until_running)

    CLASSIC_ADDRESS_RETRY_WAIT = 10
    # retry for up to 5 minutes
    MAX_CLASSIC_ADDRESS_ATTEMPTS = (60 / CLASSIC_ADDRESS_RETRY_WAIT) * 5

    @classmethod
    async def wait_for_ip_address(cls, instance):
        logging.info("Waiting until instance %s (%s) has an ip address",
            instance.id, instance.name)
        attempts = 0
        while not instance.classic_address:
            attempts += 1
            if attempts > cls.MAX_CLASSIC_ADDRESS_ATTEMPTS:
                logging.error("%sth failure to get ip address. Aborting.",
                    cls.MAX_CLASSIC_ADDRESS_ATTEMPTS)
                raise FailedToGetIpAddress()

            await tornado.gen.sleep(cls.CLASSIC_ADDRESS_RETRY_WAIT)

            instance.reload()

        # instance must have ip address at this point.
        logging.info("Instance %s has ip address %s", instance.name,
            instance.classic_address.public_ip)
