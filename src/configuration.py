import json

from awsiot.greengrasscoreipc.model import GetConfigurationResponse, GetSecretValueResponse

from src.constants import (
    CONTAINER_MAPPING_KEY,
    CONTAINER_NAME_KEY,
    DEFAULT_CONTAINER_NAME,
    DEFAULT_HOST_PORT,
    DEFAULT_HOST_VOLUME,
    HOST_PORT_KEY,
    HOST_VOLUME_KEY,
    POSTGRES_PASSWORD_KEY,
    POSTGRES_USERNAME_KEY,
)


class ComponentConfiguration:
    """
    This data class holds the configuration of the postgresql component at any given state
    """

    def __init__(self, config_response: GetConfigurationResponse, secret_reponse: GetSecretValueResponse):
        self.__host_volume = DEFAULT_HOST_VOLUME
        self.__host_port = DEFAULT_HOST_PORT
        self.__container_name = DEFAULT_CONTAINER_NAME
        self.__db_username = ""
        self.__db_password = ""

        self._set_container_config(config_response)
        self._set_credential_secret(secret_reponse)

    def _set_container_config(self, config_response: GetConfigurationResponse):
        """
        Helper function to update the container configuration.

        Args
            config_response(GetConfigurationResponse): Configuration response object obtained via IPC.

        Returns
            None
        """
        component_config = config_response.value
        if CONTAINER_MAPPING_KEY not in component_config:
            return
        container_config = component_config[CONTAINER_MAPPING_KEY]
        if HOST_PORT_KEY in container_config:
            self.__host_port = container_config[HOST_PORT_KEY]
        if HOST_VOLUME_KEY in container_config:
            self.__host_volume = container_config[HOST_VOLUME_KEY]
        if CONTAINER_NAME_KEY in container_config:
            self.__container_name = container_config[CONTAINER_NAME_KEY]

    def _set_credential_secret(self, secret_response: GetSecretValueResponse) -> None:
        """
        Sets configuration with the superuser credentials (username and password) obtained from the secrets manager
        via IPC.

        Args
            secret_response(GetSecretValueResponse): Secret value response object obtained via IPC

        Returns
            None
        """
        if not secret_response:
            return
        secret = json.loads(secret_response.secret_value.secret_string)
        self.__db_username = secret[POSTGRES_USERNAME_KEY]
        self.__db_password = secret[POSTGRES_PASSWORD_KEY]

    # Getters
    def get_db_credentials(self):
        "Returns db credentials as a tuple"
        return self.__db_username, self.__db_password

    def get_container_name(self):
        "Returns docker container name"
        return self.__container_name

    def get_host_port(self):
        "Returns docker host port"
        return self.__host_port

    def get_host_volume(self):
        "Returns docker host volume"
        return self.__host_volume
