"""SSH/SCP Client with optional context handling. For example:

> client = SshClient('sdsdf', 1.2.3.4):
> client.execute('echo Foo')
> client.close()

or

> with SshClient('sdsdf', 1.2.3.4) as client:
>     client.execute('echo Foo')

"""

import logging
import os

from fabric.connection import Connection
from invoke.exceptions import UnexpectedExit

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
            self.client = Connection(host=self._ip, user="ubuntu",
                connect_kwargs={"key_filename": self._ssh_key})

        return self.client

    async def execute(self, cmd, ignore_errors=False):
        logging.info("About to run %s on %s", cmd, self._ip)
        try:
            return await run_in_loop_executor(
                self.client.run, cmd, hide=True
            )
        except UnexpectedExit as e:
            if ignore_errors:
                return e.result
            raise

        # TODO: handle other exceptions?


    async def put(self, local_file_path, remote_file_path):
        """Uploads local file(s) to remote server, recursively if passed a
        directory.
        """
        if os.path.isdir(local_file_path):
            await self.execute('mkdir {}'.format(remote_file_path))
            for f in os.listdir(local_file_path):
                await self.put(os.path.join(local_file_path, f),
                    os.path.join(remote_file_path, f))
        else:
            await run_in_loop_executor(self.client.put, local_file_path,
                remote=remote_file_path)

    async def get(self, remote_file_path, local_file_path):
        """Downloads remote files to local file system

        TODO: Support recusrive mode if passed a directory
        """
        await run_in_loop_executor(self.client.get, remote_file_path,
            local=local_file_path)

    def close(self):
        if self.client and self.client.is_connected:
            self.client.close()
