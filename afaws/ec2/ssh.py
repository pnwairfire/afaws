"""SSH/SCP Client with optional context handling. For example:

> client = SshClient('sdsdf', 1.2.3.4):
> client.execute('echo Foo')
> client.close()

or

> with SshClient('sdsdf', 1.2.3.4) as client:
>     client.execute('echo Foo')

"""

import logging

import paramiko

from ..asyncutils import run_in_loop_executor

class SshClient(object):

    def __init__(self, ssh_key, ip):
        self._ssh_key = ssh_key
        self._ip = ip
        self.client = None

    def __enter__(self):
        self._create_client()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def _create_client(self):
        if self.client is None:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            cert = paramiko.RSAKey.from_private_key_file(self._ssh_key)
            self.client.connect(hostname=self._ip, username="ubuntu", pkey=cert)
        return self.client

    async def execute(self, cmd):
        logging.info("About to run %s on %s", cmd, self._ip)
        return await run_in_loop_executor(
            self.client.exec_command, cmd
        )

    async def put(self, local_file_path, remote_file_path):
        ftp_client = self.client.open_sftp()
        await run_in_loop_executor(ftp_client.put, local_file_path,
            remote_file_path)
        ftp_client.close()

    async def get(self, remote_file_path, local_file_path):
        ftp_client=ssh_client.open_sftp()
        await run_in_loop_executor(ftp_client.get, remote_file_path,
            local_file_path)
        ftp_client.close()

    def close(self):
        if self.client:
            self.client.close()
