import logging
import sys

import docker
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration_handler import ComponentConfigurationIPCHandler
from src.container import ContainerManagement

if __name__ == "__main__":
    # Configure logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))

    ipc_client = GreengrassCoreIPCClientV2()
    docker_client = docker.DockerClient(version="auto")
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    container_management = ContainerManagement(ipc_client, docker_client, configuration_handler)
    container_management.manage_postgresql_container(configuration_handler.get_configuration())
