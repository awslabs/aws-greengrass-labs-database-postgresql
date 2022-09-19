import logging
import sys

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
    try:
        ipc_client = GreengrassCoreIPCClientV2()
        docker_client = docker.DockerClient(version="auto")
        configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
        container_management = ContainerManagement(ipc_client, docker_client, configuration_handler)
        container_management.shutdown_container()
        ipc_client.close()
        docker_client.close()
    except Exception:
        logging.exception("Exception occurred while shutting down the component")

