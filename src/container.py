import logging
from threading import Thread

from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import ConfigurationUpdateEvents
from docker.models.containers import Container

from src.configuration import ComponentConfiguration
from src.configuration_handler import ComponentConfigurationIPCHandler
from src.constants import (
    DB_CREDENTIAL_SECRET_KEY,
    DEFAULT_CONTAINER_PORT,
    DEFAULT_CONTAINER_VOLUME,
    DEFAULT_DB_NAME,
    POSTGRES_DB_KEY,
    POSTGRES_IMAGE,
    POSTGRES_PASSWORD_KEY,
    POSTGRES_USERNAME_KEY,
)


class ContainerManagement:
    def __init__(
        self, ipc_client: GreengrassCoreIPCClientV2, docker_client: Container, config_handler: ComponentConfigurationIPCHandler
    ) -> None:
        self.__ipc_client = ipc_client
        self.config_handler = config_handler
        self.docker_client = docker_client
        self.postgresql_container = None
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

    def _on_configuration_update_event(self, events: ConfigurationUpdateEvents):
        if not events.configuration_update_event:
            return
        key_path = events.configuration_update_event.key_path
        if DB_CREDENTIAL_SECRET_KEY not in key_path:
            self.manage_postgresql_container(self.config_handler.get_configuration())

    def manage_postgresql_container(self, configuration: ComponentConfiguration):
        if not self.postgresql_container:
            try:
                self.postgresql_container = self.docker_client.containers.get(configuration.get_container_name())
            except Exception as exception:
                logging.exception(exception, exc_info=True)
        self._recreate_container(configuration)

    def _recreate_container(self, configuration):
        if self.postgresql_container:
            self._stop_container()
            self._remove_container()
        self._run_container(configuration)

    def _stop_container(self):
        logging.info("Stopping the docker container : %s", self.postgresql_container.name)
        self.postgresql_container.stop()

    def _remove_container(self):
        logging.info("Removing the docker container : %s", self.postgresql_container.name)
        self.postgresql_container.remove()

    def _run_container(self, config: ComponentConfiguration):
        db_username, db_password = config.get_db_credentials()
        postgres_env = {
            POSTGRES_USERNAME_KEY: db_username,
            POSTGRES_PASSWORD_KEY: db_password,
            POSTGRES_DB_KEY: DEFAULT_DB_NAME,
        }

        postgres_ports = {DEFAULT_CONTAINER_PORT: config.get_host_port()}
        volume_mapping = f"{config.get_host_volume()}:{DEFAULT_CONTAINER_VOLUME}"
        container_name = config.get_container_name()
        logging.info("Running the docker container : %s", container_name)
        self.postgresql_container = self.docker_client.containers.run(
            POSTGRES_IMAGE,
            name=container_name,
            ports=postgres_ports,
            environment=postgres_env,
            volumes=[volume_mapping],
            detach=True,
        )
        self._follow_container_logs()

    def _follow_container_logs(self):
        def _follow_logs():
            logs_from_container = self.postgresql_container.logs(follow=True, stream=True)
            for log in logs_from_container:
                logging.info(log.decode())

        logging.info("Following the docker container logs....")
        logs_thread = Thread(target=_follow_logs)
        logs_thread.start()
