import logging
from pathlib import Path
from threading import Lock, Thread

import docker.errors
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import ConfigurationUpdateEvents
from docker.models.containers import Container

from src.configuration import ComponentConfiguration
from src.configuration_handler import ComponentConfigurationIPCHandler
from src.constants import (
    CUSTOM_FILES,
    DEFAULT_CONTAINER_PORT,
    DEFAULT_CONTAINER_VOLUME,
    DEFAULT_DB_NAME,
    POSTGRES_COMMAND_DO_NOT_CHANGE,
    POSTGRES_DB_KEY,
    POSTGRES_IMAGE,
    POSTGRES_PASSWORD_FILE_KEY,
    POSTGRES_USERNAME_FILE_KEY,
    SECRETS_KEY,
    SUPPORTED_CONFIGURATION_FILES,
)


class ContainerManagement:
    def __init__(
        self, ipc_client: GreengrassCoreIPCClientV2, docker_client: Container, config_handler: ComponentConfigurationIPCHandler
    ) -> None:
        self.__ipc_client = ipc_client
        self.config_handler = config_handler
        self.docker_client = docker_client
        self.postgresql_container = None
        self.lock = Lock()
        self.current_configuration = config_handler.get_configuration()
        self.secrets_path = Path().joinpath(SECRETS_KEY).resolve()

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
        with self.lock:
            component_configuration = self.config_handler.get_configuration()
            if self.current_configuration != component_configuration:
                self.current_configuration = component_configuration
                self.manage_postgresql_container(component_configuration)

    def _set_container(self, configuration: ComponentConfiguration):
        if not self.postgresql_container:
            try:
                self.postgresql_container = self.docker_client.containers.get(configuration.get_container_name())
            except docker.errors.NotFound as not_found:
                logging.debug("Exception while getting the container: ", not_found.explanation)
            except Exception as exception:
                logging.exception(exception, exc_info=True)

    def manage_postgresql_container(self, configuration: ComponentConfiguration):
        self._set_container(configuration)
        logging.info("Creating a new docker container: %s as the configuration changed", configuration.get_container_name())
        self._recreate_container(configuration)

    def _recreate_container(self, configuration):
        if self.postgresql_container:
            self._stop_container()
            self._remove_container()
        self._run_container(configuration)

    def _stop_container(self):
        if not self.postgresql_container:
            return
        logging.info(
            "Stopping the docker container : {}-{}".format(self.postgresql_container.name, self.postgresql_container.id)
        )
        try:
            self.postgresql_container.stop()
        except docker.errors.NotFound as e:
            logging.debug(
                "Could not stop the container: {}-{} as it does not exist : {}".format(
                    self.postgresql_container.name, self.postgresql_container.id, e.explanation
                )
            )

    def _remove_container(self):
        if not self.postgresql_container:
            return
        logging.info(
            "Removing the docker container : {}-{}".format(self.postgresql_container.name, self.postgresql_container.id)
        )
        try:
            self.postgresql_container.remove()
        except docker.errors.NotFound as e:
            logging.debug(
                "Could not remove the container: {}-{}  as it does not exist : {}".format(
                    self.postgresql_container.name, self.postgresql_container.id, e.explanation
                )
            )

    def _get_volumes(self, config: ComponentConfiguration):
        volumes = [
            f"{config.get_host_volume()}:{DEFAULT_CONTAINER_VOLUME}",
            f"{self.secrets_path}:{CUSTOM_FILES}/{SECRETS_KEY}",
        ]

        server_configuration_files = config.get_pg_config_files()
        if not server_configuration_files:
            return volumes
        for conf_file, file_abs_path in server_configuration_files.items():
            volumes.append(f"{file_abs_path}:{CUSTOM_FILES}/{conf_file}")
        return volumes

    def _run_container(self, config: ComponentConfiguration):
        db_username, db_password = config.get_db_credentials()
        self._write_secrets_to_file(db_username, db_password)
        postgres_env = {
            POSTGRES_USERNAME_FILE_KEY: f"{CUSTOM_FILES}/{SECRETS_KEY}/{POSTGRES_USERNAME_FILE_KEY}",
            POSTGRES_PASSWORD_FILE_KEY: f"{CUSTOM_FILES}/{SECRETS_KEY}/{POSTGRES_PASSWORD_FILE_KEY}",
            POSTGRES_DB_KEY: DEFAULT_DB_NAME,
        }

        postgres_ports = {DEFAULT_CONTAINER_PORT: config.get_host_port()}
        container_name = config.get_container_name()
        logging.info("Running the docker container : %s", container_name)

        self.postgresql_container = self.docker_client.containers.run(
            POSTGRES_IMAGE,
            "{} {}".format(POSTGRES_COMMAND_DO_NOT_CHANGE, self._create_config_command(config)),
            name=container_name,
            ports=postgres_ports,
            environment=postgres_env,
            volumes=self._get_volumes(config),
            detach=True,
        )
        self._follow_container_logs()

    def _write_secrets_to_file(self, db_username, db_password):
        db_user_path = self.secrets_path.joinpath(POSTGRES_USERNAME_FILE_KEY).resolve()
        db_password_path_ = self.secrets_path.joinpath(POSTGRES_PASSWORD_FILE_KEY).resolve()
        try:
            # Create secrets directory if it
            self.secrets_path.mkdir(parents=True, exist_ok=True)
            # Write secret files
            with open(db_user_path, "w") as u_file:
                u_file.write(db_username)
            with open(db_password_path_, "w") as p_file:
                p_file.write(db_password)
        except Exception as e:
            logging.exception("Exception while writing the secrets files: ", e)

    def _create_config_command(self, config):
        command = ""
        server_configuration_files = config.get_pg_config_files()
        if not server_configuration_files:
            return command
        for conf_file in server_configuration_files.keys():
            command = command + " -c {}={}".format(SUPPORTED_CONFIGURATION_FILES[conf_file], f"{CUSTOM_FILES}/{conf_file}")
        return command

    def _follow_container_logs(self):
        def _follow_logs():
            logs_from_container = self.postgresql_container.logs(follow=True, stream=True)
            for log in logs_from_container:
                logging.info(log.decode())

        logging.info(
            "Following the docker container: {}-{} logs....".format(
                self.postgresql_container.name, self.postgresql_container.id
            )
        )
        logs_thread = Thread(target=_follow_logs)
        logs_thread.start()
