import os

HOST_PORT_KEY = "HostPort"
HOST_VOLUME_KEY = "HostVolume"
CONTAINER_NAME_KEY = "ContainerName"
CONTAINER_MAPPING_KEY = "ContainerMapping"
DB_CREDENTIAL_SECRET_KEY = "DBCredentialSecret"
POSTGRES_USERNAME_KEY = "postgresql_username"
POSTGRES_PASSWORD_KEY = "postgresql_password"
DEFAULT_HOST_PORT = "5432"
DEFAULT_CONTAINER_NAME = "greengrass_postgresql"
DEFAULT_HOST_VOLUME = f"{os.getcwd()}/postgresql"
