from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import ConfigurationUpdateEvents

import src.constants as consts


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

        def on_configuration_update_event(event: ConfigurationUpdateEvents):
            # Will manage docker container based on updates
            print(event)

        self.__ipc_client.subscribe_to_configuration_update(
            on_stream_event=on_configuration_update_event, on_stream_error=None, on_stream_closed=None
        )

    def get_configuration(self):
        """
        Gets the current configuration of the component.

        Args
            None

        Returns
            None
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
            if "HostPort" in container_params:
                self.__component_configuration.host_port = container_params["HostPort"]
            if "HostVolume" in container_params:
                self.__component_configuration.host_volume = container_params["HostVolume"]
            if "ContainerName" in container_params:
                self.__component_configuration.container_name = container_params["ContainerName"]

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
            self.__component_configuration.db_username = secret["postgresql_username"]
            self.__component_configuration.db_password = secret["postgresql_password"]

        if "ContainerMapping" in config:
            container_config = config["ContainerMapping"]
            _set_container_config(container_config)

        if "CredentialSecret" in config:
            _set_credential_secret(config["CredentialSecret"])

    class __ComponentConfiguration:
        """
        This object holds the configuration of the postgresql component at any given state
        """

        def __init__(self):
            self.host_volume = consts.DEFAULT_HOST_VOLUME
            self.host_port = consts.DEFAULT_HOST_PORT
            self.container_name = consts.DEFAULT_CONTAINER_NAME
            self.db_username = ""
            self.db_password = ""
