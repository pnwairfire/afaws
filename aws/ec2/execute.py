import asyncio
import logging
import time
from collections import defaultdict

#import boto3
import paramiko
import tornado.gen

from .resources import Instance

__all__ = [
    'FailedToSshError',
    'Ec2SshExecuter'
]

class FailedToSshError(RuntimeError):
    pass

class Ec2SshExecuter(object):

    def __init__(self, ssh_key, instances_or_identifiers):
        # accept single stirng value for 'commands'
        if not hasattr(instances_or_identifiers, 'append'):
            instances_or_identifiers = [instances_or_identifiers]
        self._instances_or_identifiers = instances_or_identifiers

        self._cert = paramiko.RSAKey.from_private_key_file(ssh_key)
        self._ips = None

    async def ips(self):
        if self._ips is None:
            self._ips = [(await Instance(i)).classic_address.public_ip
                for i in self._instances_or_identifiers]
        return self._ips

    SSH_RETRY_WAIT = 10
    MAX_SSH_ATTEMPTS = (60 / SSH_RETRY_WAIT) * 5 # retry for up to 5 minutes
    # SSH_EXCEPTION_CLASSES = (
    #     paramiko.ssh_exception.PasswordRequiredException,
    #     paramiko.ssh_exception.NoValidConnectionsError
    #     # TODO: add other exception classes ?
    # )
    async def wait_for_ssh_connectivity(self):
        logging.info("Waiting for ssh connectivity to %s", await self.ips())
        attempts = 0
        while True:
            try:
                await self.execute('ls /')
                return

            #except self.SSH_EXCEPTION_CLASSES as e:
            except Exception as e:
                # TODO: handle ConnectionResetError as well
                if e.__class__.__module__ != 'paramiko.ssh_exception':
                    raise

                attempts += 1
                if attempts >= self.MAX_SSH_ATTEMPTS:
                    logging.error("%sth SSH failure. Aborting.", self.MAX_SSH_ATTEMPTS)
                    raise FailedToSshError()

                logging.info("SSH failure. waiting %s seconds before trying again",
                    self.SSH_RETRY_WAIT)
                await tornado.gen.sleep(self.SSH_RETRY_WAIT)


    async def execute(self, commands):
        # accept single stirng value for 'commands'
        if hasattr(commands, 'lower'):
            commands = [commands]

        logging.info("Executing commands on %s", await self.ips())
        output = {
            "STDERR": defaultdict(lambda: []),
            "STDOUT": defaultdict(lambda: [])
        }
        await asyncio.gather(*[
            self._execute_commands(commands, ip, output)
                for ip in await self.ips()
        ])
        return output

    async def _execute_commands(self, commands, ip, output):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(hostname=ip, username="ubuntu", pkey=self._cert)

        for cmd in commands:
            logging.info("Running %s on %s", cmd, ip)
            stdin, stdout, stderr = client.exec_command(cmd)

            # TODO: check return code somehow, and abort or at least give error message
            #   if failed?  <-- would nee to know to skip some errors (e.g. dont
            #   abort if mount failes due to volume being already mounted)
            for k in ('STDOUT', 'STDERR'):
                o = stdout if k == 'STDOUT' else stderr
                log_func = logging.debug if k == 'STDOUT' else logging.warn
                out = o.readlines()
                self._log_output(cmd, ip, out, log_func, k)
                if out:
                    output[k][ip].append((cmd, out))

        client.close()

    def _log_output(self, cmd, ip, lines, log_func, stream_name):
            if lines:
                log_func("%s of %s on %s: ", stream_name, cmd, ip)
                for l in lines:
                    log_func("  [%s]: %s", ip, l.strip())




# Note: couldn't get SSM tow ork

# class Ec2SsmExecuter(object):

#     def __init__(self, instance_identifiers):
#         self._ssm_client = boto3.client('ssm')
#         self._instance_ids = [Instance(i).id for i in instance_identifiers]

#     def execute(self, commands):
#         logging.info("Executing commands on %s", self._instance_ids)
#         r = self._ssm_client.send_command(
#             DocumentName="AWS-RunShellScript", # One of AWS' preconfigured documents
#             Parameters={'commands': commands},
#             InstanceIds=self._instance_ids,
#         )
#         output = {i: ssm_client.get_command_invocation(
#               CommandId=r['Command']['CommandId'],
#               InstanceId=i,
#             ) for i in self._instance_ids}
#         return output
