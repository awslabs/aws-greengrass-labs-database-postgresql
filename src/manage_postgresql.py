import logging
import sys
import time

import docker
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration_handler import ComponentConfigurationIPCHandler
from src.container import ContainerManagement


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))


if __name__ == "__main__":
    configure_logging()

    ipc_client = GreengrassCoreIPCClientV2()
    docker_client = docker.DockerClient(version="auto")
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    container_management = ContainerManagement(ipc_client, docker_client, configuration_handler)
    container_management.subscribe_to_configuration_updates()
    container_management.manage_postgresql_container(configuration_handler.get_configuration())
    # Keep the main thread alive to listen for component updates
    while True:
        time.sleep(5)
