import logging
import sys

import docker
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration_handler import ComponentConfigurationIPCHandler


def configure_logging():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler(sys.stdout))


def cleanup_container(docker_client, container_name):
    try:
        postgresql_container = docker_client.containers.get(container_name)
        if postgresql_container:
            postgresql_container.stop()
            postgresql_container.remove()
    except Exception:
        logging.exception("Exception occurred while removing the container")


def main():
    configure_logging()
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    container_name = configuration_handler.get_configuration().get_container_name()
    docker_client = docker.DockerClient(version="auto")
    cleanup_container(docker_client, container_name)


if __name__ == "__main__":
    main()
