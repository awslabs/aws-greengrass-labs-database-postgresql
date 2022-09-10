import os

HOST_PORT_KEY = "HostPort"
HOST_VOLUME_KEY = "HostVolume"
CONTAINER_NAME_KEY = "ContainerName"
DEFAULT_HOST_PORT = "5432"
DEFAULT_CONTAINER_NAME = "greengrass_postgresql"
DEFAULT_HOST_VOLUME = f"{os.getcwd()}/postgresql"
