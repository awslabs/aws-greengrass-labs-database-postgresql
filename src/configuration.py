import logging

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import ConfigurationUpdateEvents

from src.constants import (
    CONTAINER_NAME_KEY,
    DEFAULT_CONTAINER_NAME,
    DEFAULT_HOST_PORT,
    DEFAULT_HOST_VOLUME,
    HOST_PORT_KEY,
    HOST_VOLUME_KEY,
)


class ComponentConfigurationHandler:
    """
    This is used to manage the PostgreSQL component configuration and handle updates on it.
    """

    def __init__(self) -> None:
        self.__ipc_client = GreengrassCoreIPCClientV2()
        self.__component_configuration = self.__ComponentConfiguration()

    def subscribe_to_configuration_updates(self):
        """
        Subscribes to the component configuration updates over IPC using callbacks for the stream events.
        Any new configuration update to the component triggers on_stream_event -> on_configuration_update_event callback.

        Args
            None

        Returns
            None
        """

        def __on_configuration_update_event(event: ConfigurationUpdateEvents):
            # Will manage docker container based on updates
            print(event)

        def __on_stream_error_event(error: Exception) -> bool:
            logging.error("Exception occurred in the stream while subscribing to the  configuration updates", exc_info=error)
            return False  # Keeps the stream open

        def __on_stream_closed_event():
            logging.info("Subscribe to configuration update stream closed.")

        self.__ipc_client.subscribe_to_configuration_update(
            on_stream_event=__on_configuration_update_event,
            on_stream_error=__on_stream_error_event,
            on_stream_closed=__on_stream_closed_event,
        )

    def get_configuration(self):
        """
        Gets the current configuration of the component.

        Args
            None

        Returns
            ComponentConfiguration data object that holds the latest configuration
        """
        response = self.__ipc_client.get_configuration()
        self.__set_config(response.value)
        return self.__component_configuration

    def __set_config(self, config) -> None:
        """
        Updates the component configuration object if the values are set. Otherwise, default values are used.

        Args
            config(dict): JSON object with configuration keys and values.

        Returns
            None
        """

        def _set_container_config(container_params):
            """
            Helper function to update the container configuration.

            Args
                container_params(dict): JSON object with container configuration key and values.

            Returns
                None
            """
            if HOST_PORT_KEY in container_params:
                self.__component_configuration.set_host_port(container_params[HOST_PORT_KEY])
            if HOST_VOLUME_KEY in container_params:
                self.__component_configuration.set_host_volume(container_params[HOST_VOLUME_KEY])
            if CONTAINER_NAME_KEY in container_params:
                self.__component_configuration.set_container_name(container_params[CONTAINER_NAME_KEY])

        def _set_credential_secret(secret_id) -> None:
            """
            Sets configuration with the superuser credentials (username and password) obtained from the secrets manager
            via IPC.

            Args
                secret_id(String): Secrets arn of the credentials.

            Returns
                None
            """
            response = self.__ipc_client.get_secret_value(secret_id=secret_id)
            secret = response.secret_value.secret_string
            self.__component_configuration.set_db_credentials(
                db_username=secret["postgresql_username"], db_password=secret["postgresql_password"]
            )

        if "ContainerMapping" in config:
            container_config = config["ContainerMapping"]
            _set_container_config(container_config)

        if "CredentialSecret" in config:
            _set_credential_secret(config["CredentialSecret"])

    class __ComponentConfiguration:
        """
        This data class holds the configuration of the postgresql component at any given state
        """

        def __init__(self):
            self.__host_volume = DEFAULT_HOST_VOLUME
            self.__host_port = DEFAULT_HOST_PORT
            self.__container_name = DEFAULT_CONTAINER_NAME
            self.__db_username = ""
            self.__db_password = ""

        # Setters
        def set_db_credentials(self, db_username, db_password):
            "Sets db credentials - username and password"
            self.__db_username = db_username
            self.__db_password = db_password

        def set_container_name(self, container_name):
            "Sets docker container name"
            self.__container_name = container_name

        def set_host_port(self, host_port):
            "Sets docker host port"
            self.__host_port = host_port

        def set_host_volume(self, host_volume):
            "Sets docker host volume"
            self.__host_volume = host_volume

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
