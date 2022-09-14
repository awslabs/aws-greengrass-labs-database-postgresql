from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import ConfigurationUpdateEvents, SubscribeToConfigurationUpdateResponse
from src.configuration_handler import ComponentConfigurationIPCHandler
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

    mock_subscribe_config = mocker.patch.object(
        mock_ipc_client, "subscribe_to_configuration_update", side_effect=this_triggers_callbacks
    )
    mock_manage_postgresql_contaienr = mocker.patch.object(
        ContainerManagement, "manage_postgresql_container", return_value=None
    )
    ContainerManagement(mock_ipc_client, mock_configuration_handler)

    assert mock_subscribe_config.call_count == 1
    assert mock_manage_postgresql_contaienr.call_count == 1
