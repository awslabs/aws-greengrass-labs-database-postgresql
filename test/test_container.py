import docker
import pytest
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import (
    ConfigurationUpdateEvent,
    ConfigurationUpdateEvents,
    GetConfigurationResponse,
    GetSecretValueResponse,
    SecretValue,
    SubscribeToConfigurationUpdateResponse,
)
from docker.models.containers import Container, ContainerCollection
from src.configuration import ComponentConfiguration
from src.configuration_handler import ComponentConfigurationIPCHandler
from src.constants import POSTGRES_IMAGE, POSTGRES_PASSWORD_FILE_KEY, POSTGRES_USERNAME_FILE_KEY
from src.container import ContainerManagement


@pytest.fixture()
def change_test_dir(tmpdir, monkeypatch):
    monkeypatch.chdir(tmpdir)
    return tmpdir


def test_container_management_update_event(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mock_ipc_client = GreengrassCoreIPCClientV2()
    mock_configuration_handler = ComponentConfigurationIPCHandler(mock_ipc_client)

    def this_triggers_callbacks(*args, **kwargs):
        config_update_events = ConfigurationUpdateEvents()
        kwargs["on_stream_event"](config_update_events)
        return SubscribeToConfigurationUpdateResponse()

    mocker.patch.object(mock_ipc_client, "subscribe_to_configuration_update", side_effect=this_triggers_callbacks)
    mocker.patch.object(ContainerManagement, "manage_postgresql_container", return_value=None)

    ContainerManagement(mock_ipc_client, None, mock_configuration_handler)


def test_container_management_create_or_recreate_container(mocker, change_test_dir):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mock_ipc_client = GreengrassCoreIPCClientV2()
    mock_configuration_handler = ComponentConfigurationIPCHandler(mock_ipc_client)

    def this_triggers_callbacks(*args, **kwargs):
        config_update_events = ConfigurationUpdateEvents(
            configuration_update_event=ConfigurationUpdateEvent(component_name="", key_path="/some/path")
        )
        kwargs["on_stream_event"](config_update_events)
        return SubscribeToConfigurationUpdateResponse()

    mocker.patch.object(mock_ipc_client, "subscribe_to_configuration_update", side_effect=this_triggers_callbacks)
    mock_get_configuration_response = GetConfigurationResponse(
        value={
            "ContainerMapping": {
                "HostPort": "8000",
                "HostVolume": "/some/volume/",
                "ContainerName": "some-container-name",
                "DBCredentialSecret": "secret",
            }
        }
    )
    secret_value_reponse = GetSecretValueResponse(
        secret_value=SecretValue(
            secret_string='{"POSTGRES_USER": "this-is-a-username", "POSTGRES_PASSWORD": "Thi5-is-@-password"}'
        )
    )
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=mock_get_configuration_response)
    mock_container = Container()
    mocker.patch("docker.DockerClient.containers", return_value=ContainerCollection())
    mocker.patch("threading.Thread", return_value=None)
    mocker.patch.object(docker.DockerClient.containers, "get", side_effect=Exception("Container does not exist"))
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    mock_run_container = mocker.patch.object(docker.DockerClient.containers, "run", return_value=mock_container)
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_logs_container = mocker.patch.object(Container, "logs", return_value=[])
    cm = ContainerManagement(mock_ipc_client, docker.DockerClient, mock_configuration_handler)
    cm.current_configuration = ComponentConfiguration(mock_get_configuration_response, secret_value_reponse)
    cm.subscribe_to_configuration_updates()
    assert not mock_remove_container.called
    assert not mock_stop_container.called

    assert mock_run_container.called
    assert mock_logs_container.called
    mocker.patch.object(docker.DockerClient.containers, "get", return_value=mock_container)
    cm.manage_postgresql_container(mock_configuration_handler.get_configuration())

    assert mock_remove_container.called
    assert mock_stop_container.called

    assert mock_run_container.called
    assert mock_logs_container.called


def test_container_management_run_container(mocker, change_test_dir):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mock_ipc_client = GreengrassCoreIPCClientV2()
    mock_configuration_handler = ComponentConfigurationIPCHandler(mock_ipc_client)

    def this_triggers_callbacks(*args, **kwargs):
        config_update_events = ConfigurationUpdateEvents(
            configuration_update_event=ConfigurationUpdateEvent(component_name="", key_path=["some"])
        )
        kwargs["on_stream_event"](config_update_events)
        return SubscribeToConfigurationUpdateResponse()

    mocker.patch.object(mock_ipc_client, "subscribe_to_configuration_update", side_effect=this_triggers_callbacks)
    mock_get_configuration_response = GetConfigurationResponse(
        value={
            "ContainerMapping": {
                "HostPort": "8000",
                "HostVolume": "/some/volume/",
                "ContainerName": "some-container-name",
            },
            "DBCredentialSecret": "secret",
            "ConfigurationFiles": {"postgresql.conf": "/path/to/custom/postgresql.conf"},
        }
    )
    secret_value_reponse = GetSecretValueResponse(
        secret_value=SecretValue(
            secret_string='{"POSTGRES_USER": "this-is-a-username", "POSTGRES_PASSWORD": "Thi5-is-@-password"}'
        )
    )
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=mock_get_configuration_response)
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_secret_value", return_value=secret_value_reponse)
    mocker.patch("docker.DockerClient.containers", return_value=ContainerCollection())
    mocker.patch.object(docker.DockerClient.containers, "get", side_effect=Exception("Container does not exist"))
    spy_docker_run = mocker.spy(docker.DockerClient.containers, "run")
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    mocker.patch("pathlib.Path.is_file", return_value=True)
    cm = ContainerManagement(mock_ipc_client, docker.DockerClient, mock_configuration_handler)
    cm.current_configuration = ComponentConfiguration(mock_get_configuration_response, None)
    cm.subscribe_to_configuration_updates()
    assert not mock_remove_container.called
    assert not mock_stop_container.called
    args, kwargs = spy_docker_run.call_args
    assert cm.secrets_path.exists()
    assert cm.secrets_path.joinpath(POSTGRES_PASSWORD_FILE_KEY).is_file()
    assert cm.secrets_path.joinpath(POSTGRES_USERNAME_FILE_KEY).is_file()
    assert POSTGRES_IMAGE in args[0]
    assert kwargs["name"] == "some-container-name"
    assert kwargs["detach"]
    assert kwargs["environment"] == {
        "POSTGRES_USER_FILE": "/custom_files/secrets/POSTGRES_USER_FILE",
        "POSTGRES_PASSWORD_FILE": "/custom_files/secrets/POSTGRES_PASSWORD_FILE",
        "POSTGRES_DB": "postgres",
    }


def test_container_management_no_update_when_same_configuration(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mock_ipc_client = GreengrassCoreIPCClientV2()
    mock_configuration_handler = ComponentConfigurationIPCHandler(mock_ipc_client)

    def this_triggers_callbacks(*args, **kwargs):
        config_update_events = ConfigurationUpdateEvents(
            configuration_update_event=ConfigurationUpdateEvent(
                component_name="", key_path=["ConfigurationFiles", "postgresql.conf"]
            )
        )
        kwargs["on_stream_event"](config_update_events)
        return SubscribeToConfigurationUpdateResponse()

    mocker.patch.object(mock_ipc_client, "subscribe_to_configuration_update", side_effect=this_triggers_callbacks)
    mock_get_configuration_response = GetConfigurationResponse(
        value={
            "ContainerMapping": {
                "HostPort": "8000",
                "HostVolume": "/some/volume/",
                "ContainerName": "some-container-name",
                "DBCredentialSecret": "secret",
            },
            "ConfigurationFiles": {"postgresql.conf": "/path/to/custom/postgresql.conf"},
        }
    )

    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=mock_get_configuration_response)
    mocker.patch("threading.Thread", return_value=None)
    mocker.patch("docker.DockerClient.containers", return_value=ContainerCollection())
    mocker.patch.object(docker.DockerClient.containers, "get", return_value=Container())
    mocker.patch("pathlib.Path.is_file", return_value=True)
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    mock_run_container = mocker.patch.object(docker.DockerClient.containers, "run", return_value=None)
    mock_restart_container = mocker.patch.object(Container, "restart", return_value=None)
    mock_logs_container = mocker.patch.object(Container, "logs", return_value=[])

    cm = ContainerManagement(mock_ipc_client, docker.DockerClient, mock_configuration_handler)
    cm.subscribe_to_configuration_updates()
    assert not mock_remove_container.called
    assert not mock_stop_container.called
    assert not mock_run_container.called
    assert not mock_restart_container.called
    assert not mock_logs_container.called
