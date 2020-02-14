import asyncio
import logging
import os
import sys

from .execute import Ec2SshExecuter

__all__ = [
    'InstanceInitializer'
]

class InstanceInitializerSsh(object):

    def __init__(self, ssh_key, config, emulate=None):
        self._config = config
        self._ssh_key = ssh_key
        self._emulate = emulate
        self._executer = None
        self._efs_volumes = self._config('default_efs_volumes')
        self._yaml_files = None
        self._makefiles = None

    async def initialize(self, instances_or_identifiers):
        await self._initialize_self()

        # Note: We're not assuming that instances are all clones of the same
        # source instance, so we'll search for docker-compose yaml files
        # and Makefiles on each
        await asyncio.gather(*[
            self._initialize_instance(i) for i in instances_or_identifiers
        ])

    ## General helpers

    async def _initialize_self(self):
        # Initialize if 'emulate' was specified, but only do it once
        # this has to be called from 'initialize' because __inii__ can be async
        if self._emulate and not self._executer:
            if self._emulate:
                self._executer = Ec2SshExecuter(self._ssh_key, self._emulate)
                self._efs_volumes = await self._find_efs_volumes(self._executer)
                self._yaml_files = await self._find_yaml_files(self._executer)
                self._makefiles = await self._find_makefiles(self._executer)

    async def _initialize_instance(self, instance_or_identifier):
        executer = Ec2SshExecuter(self._ssh_key, instance_or_identifier)
        await executer.wait_for_ssh_connectivity()
        cmds = (
                await self._get_mount_efs_volumes_cmds(executer)
                + await self._get_restart_docker_cmd(executer)
                + await self._get_restart_docker_compose_cmds(executer)
                + await self._get_restart_make_cmds(executer)
            )
        await executer.execute(cmds, ignore_errors=True)

    async def _find_files(self, executer, root_dirs, filename_pattern, maxdepth=2):
        files = []
        for root_dir in root_dirs:
            cmd = "sudo find {} -name {} -maxdepth {}".format(root_dir,
                filename_pattern, maxdepth)
            output = await executer.execute(cmd)
            if output['STDOUT']:
                files.extend([
                    f.strip() for f in list(output['STDOUT'].items())[0][1][0][1]
                ])
        return files

    ## Mount Commands

    async def _find_efs_volumes(self, executer):
        logging.info("Finding EFS volumes on %s", executer._ips)
        cmd = "mount |grep aws |sed -e 's/ on / /g'|sed -e 's/ type .*//g'"
        output = await executer.execute(cmd)
        output_lines = list(output['STDOUT'].items())[0][1][0][1]
        return [l.strip().split(' ') for l in output_lines]

    async def _get_mount_efs_volumes_cmds(self, executer):
        def _mnt_cmd(vol):
            return ("sudo mkdir -p {dir} && sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,"
                "wsize=1048576,hard,timeo=600,retrans=2,noresvport "
                "{host_vol} {dir}").format(host_vol=vol[0], dir=vol[1])
        return [_mnt_cmd(vol) for vol in self._efs_volumes]

    ## Docker commands

    async def _get_restart_docker_cmd(self, executer):
        return ["sudo service docker restart"]

    ## Docker Compose Commmands

    async def _find_yaml_files(self, executer):
        logging.info("Finding yaml files on %s", executer._ips)
        return await self._find_files(executer,
            self._config('docker_compose_yaml_root_dirs'),
            'docker-compose*.yml')

    async def _get_restart_docker_compose_cmds(self, executer):
        yaml_files = self._yaml_files or await self._find_yaml_files(executer)
        cmds = []
        for yaml_file in yaml_files:
            cmds.extend([
                "docker-compose -f {} down --remove-orphans".format(yaml_file),
                "docker-compose -f {} up -d".format(yaml_file)
            ])
        return cmds

    ## Make Commands

    async def _find_makefiles(self, executer):
        logging.info("Finding Makefiles on %s", executer._ips)
        return await self._find_files(executer,
            self._config('makefile_root_dirs'), 'Makefile')

    async def _get_restart_make_cmds(self, executer):
        makefiles = self._makefiles or await self._find_makefiles(executer)
        makefile_dirs = [os.path.dirname(m) for m in makefiles]
        return ["cd {} && make production_bounce".format(make_dir)
            for make_dir in makefile_dirs]





# Note: couldn't get SSM tow ork

# class InstanceInitializerSsm(object):

#     async def initialize(self, instances_or_identifiers):
#         self._ec2_ssm_executer = Ec2Commander(instances_or_identifiers)

#         self._mount_efs_volumes()
#         self._restart_docker_compose()
#         self._restart_make()

#     def _mount_efs_volumes(self):
#         cmds = [("sudo mount -t nfs4 -o nfsvers=4.1,rsize=1048576,"
#                  "wsize=1048576,hard,timeo=600,retrans=2,noresvport "
#                  "{}/ {}".format(vol[0], vol[1])) for vol in self._config('default_efs_volumes')]
#         self._ec2_ssm_executer.execute(cmds)

#     def _restart_docker_compose(self):
#         cmds = []
#         for yaml_file in DOCKER_COMPOSE_YAML_FILES:
#             cmds.extend("docker-compose -f {} down".format(yaml_file))
#             cmds.extend("docker-compose -f {} up -d".format(yaml_file))
#         self._ec2_ssm_executer.execute(cmds)

#     def _restart_make(self):
#         cmds = ["cd {} && make production_bounce".format(d)
#             for d in MAKEFILE_DIRS]
#         self._ec2_ssm_executer.execute(cmds)
