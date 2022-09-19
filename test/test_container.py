import docker
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import (
    ConfigurationUpdateEvent,
    ConfigurationUpdateEvents,
    GetConfigurationResponse,
    SubscribeToConfigurationUpdateResponse,
)
from docker.models.containers import Container, ContainerCollection
from src.configuration_handler import ComponentConfigurationIPCHandler
from src.constants import POSTGRES_IMAGE
from src.container import ContainerManagement


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


def test_container_management_create_or_recreate_container(mocker):
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


def test_container_management_run_container(mocker):
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
            },
            "ConfigurationFiles": {"postgresql.conf": "/path/to/custom/postgresql.conf"},
        }
    )

    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=mock_get_configuration_response)

    mocker.patch("docker.DockerClient.containers", return_value=ContainerCollection())
    mocker.patch.object(docker.DockerClient.containers, "get", side_effect=Exception("Container does not exist"))
    spy_docker_run = mocker.spy(docker.DockerClient.containers, "run")
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    cm = ContainerManagement(mock_ipc_client, docker.DockerClient, mock_configuration_handler)
    cm.subscribe_to_configuration_updates()
    assert not mock_remove_container.called
    assert not mock_stop_container.called
    args, kwargs = spy_docker_run.call_args
    assert POSTGRES_IMAGE in args[0]
    assert kwargs["name"] == "some-container-name"
    assert kwargs["detach"]
