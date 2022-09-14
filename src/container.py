import logging

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration import ComponentConfiguration
from src.configuration_handler import ComponentConfigurationIPCHandler


class ContainerManagement:
    def __init__(self, ipc_client: GreengrassCoreIPCClientV2, config_handler: ComponentConfigurationIPCHandler) -> None:
        self.__ipc_client = ipc_client
        self.config_handler = config_handler
        self.subscribe_to_configuration_updates()

    def subscribe_to_configuration_updates(self):
        """
        Subscribes to the component configuration updates over IPC using callbacks for the stream events.
        Any new configuration update to the component triggers on_stream_event -> on_configuration_update_event callback.

        Args
        None

        Returns
        None
        """

        def __on_stream_error_event(error: Exception) -> bool:
            logging.error("Exception occurred in the stream while subscribing to the configuration updates", exc_info=error)
            return False  # Keeps the stream open

        def __on_stream_closed_event():
            logging.info("Subscribe to configuration update stream closed.")

        self.__ipc_client.subscribe_to_configuration_update(
            on_stream_event=self._on_configuration_update_event,
            on_stream_error=__on_stream_error_event,
            on_stream_closed=__on_stream_closed_event,
        )

    def _on_configuration_update_event(self, event):
        print(event)
        # self.manage_postgresql_container(self.config_handler.get_configuration())

    def manage_postgresql_container(self, configuration: ComponentConfiguration):
        # TODO: Use configuration
        print(configuration)

        raise Exception("Not implemented")

    def stop_container(self):
        raise Exception("Not implemented")

    def remove_container(self):
        raise Exception("Not implemented")

    def run_container(self):
        raise Exception("Not implemented")
