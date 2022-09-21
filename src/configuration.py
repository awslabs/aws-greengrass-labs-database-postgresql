import json
import logging
import re
from pathlib import Path

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
    POSTGRES_SERVER_CONFIGURATION_FILES_KEY,
    POSTGRES_USERNAME_KEY,
    SUPPORTED_CONFIGURATION_FILES,
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
        self.__pg_config_files = {}
        self._set_container_config(config_response)
        self._set_credential_secret(secret_reponse)
        self._set_configuration_files(config_response)

    def __eq__(self, other):
        return (
            self.get_container_name() == other.get_container_name()
            and self.get_container_name() == other.get_container_name()
            and self.get_host_volume() == other.get_host_volume()
            and self.get_host_port() == other.get_host_port()
            and self.get_db_credentials() == other.get_db_credentials()
            and self.get_pg_config_files() == other.get_pg_config_files()
        )

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
        if container_config.get(HOST_PORT_KEY):
            self.__host_port = container_config[HOST_PORT_KEY]
        if container_config.get(HOST_VOLUME_KEY):
            self.__host_volume = container_config[HOST_VOLUME_KEY]
        if container_config.get(CONTAINER_NAME_KEY):
            self.__container_name = container_config[CONTAINER_NAME_KEY]

    def _set_configuration_files(self, config_response):
        component_config = config_response.value
        if POSTGRES_SERVER_CONFIGURATION_FILES_KEY not in component_config:
            return
        server_configuration_files = component_config[POSTGRES_SERVER_CONFIGURATION_FILES_KEY]
        if not server_configuration_files:
            return
        for conf_file, file_path in server_configuration_files.items():
            if conf_file not in SUPPORTED_CONFIGURATION_FILES:
                logging.warning(
                    "{} will not be used as is not a supported config file. Supported configuration files: {} ".format(
                        conf_file, SUPPORTED_CONFIGURATION_FILES
                    )
                )
                continue

            conf_file_abs_path = Path(file_path).absolute()
            if not conf_file_abs_path.is_file():
                logging.warning("{} will not be used as is not a valid file path.".format(conf_file_abs_path))
                continue
            self.__pg_config_files[conf_file] = conf_file_abs_path

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
        if POSTGRES_USERNAME_KEY not in secret or POSTGRES_PASSWORD_KEY not in secret:
            raise Exception(
                "Missing postgresql credentials. Please provide a valid secret with postgresql username"
                f" ({POSTGRES_USERNAME_KEY}) and password ({POSTGRES_PASSWORD_KEY}) credentials."
            )

        if not self._valid_password(secret[POSTGRES_PASSWORD_KEY]):
            raise Exception(
                "Invalid postgresql password. Password must be at least 16 character long with uppercase and lowercase"
                " letters, numbers, and special characters."
            )
        self.__db_username = secret[POSTGRES_USERNAME_KEY]
        self.__db_password = secret[POSTGRES_PASSWORD_KEY]

    def _valid_password(self, password):
        if len(password) < 16:
            logging.warning("The length of the postgresql password should be at least 16 character long")
            return False
        if not re.search("[0-9]", password):
            logging.warning("Provided postgresql password should contain at least one digit")
            return False
        if not re.search("[a-z]", password):
            logging.warning("Provided postgresql password should contain at least one lowercase letter")
            return False
        if not re.search("[A-Z]", password):
            logging.warning("Provided postgresql password should contain at least one uppercase letter")
            return False
        if not re.search("[^a-zA-Z0-9]", password):
            logging.warning("Provided postgresql password should contain at least one special character")
            return False
        return True

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

    def get_pg_config_files(self):
        "Returns server configuration files"
        return self.__pg_config_files
