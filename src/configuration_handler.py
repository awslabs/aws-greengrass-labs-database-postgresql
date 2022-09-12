import logging

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import ConfigurationUpdateEvents, GetConfigurationResponse, GetSecretValueResponse

from src.configuration import ComponentConfiguration
from src.constants import DB_CREDENTIAL_SECRET_KEY


class ComponentConfigurationIPCHandler:
    """
    This is used to manage the PostgreSQL component configuration and handle updates on it.
    """

    def __init__(self, ipc_client: GreengrassCoreIPCClientV2) -> None:
        self.__ipc_client = ipc_client

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

    def get_configuration(self) -> ComponentConfiguration:
        """
        Gets the current configuration of the component. Also, includes IPC calls to get the secret from secrets manager.

        Args
            None

        Returns
            ComponentConfiguration data object that holds the latest configuration
        """
        config_response = self.__ipc_client.get_configuration()
        secret_response = self.__retrieve_secret(config_response)
        return ComponentConfiguration(config_response, secret_response)

    def __retrieve_secret(self, config_response: GetConfigurationResponse) -> GetSecretValueResponse:
        """
        Retrieve credentials from the secrets manager for the secret arn provided in the configuration.

        Args
            config_response(GetConfigurationResponse): Configuration response object obtained via IPC.

        Returns
            response(GetSecretValueResponse): Returns secret value reponse obtained via IPC
        """
        config = config_response.value
        if DB_CREDENTIAL_SECRET_KEY not in config:
            return None
        return self.__ipc_client.get_secret_value(secret_id=config[DB_CREDENTIAL_SECRET_KEY])
