import src.constants as consts
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import GetConfigurationResponse, GetSecretValueResponse, SecretValue
from src.configuration import ComponentConfigurationHandler


def test_configuration_default_values(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mock_ipc_client = GreengrassCoreIPCClientV2()
    configuration_handler = ComponentConfigurationHandler(mock_ipc_client)

    configuration = configuration_handler.get_configuration()
    assert configuration.get_container_name() == "greengrass_postgresql"
    assert configuration.get_db_credentials() == ("", "")
    assert configuration.get_host_volume() == consts.DEFAULT_HOST_VOLUME
    assert configuration.get_host_port() == consts.DEFAULT_HOST_PORT


def test_configuration_set_container_config(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    get_configuration_response = GetConfigurationResponse(
        value={"ContainerMapping": {"HostPort": "8000", "HostVolume": "/some/volume/", "ContainerName": "some-container-name"}}
    )
    mock_ipc_get_config = mocker.patch.object(
        GreengrassCoreIPCClientV2, "get_configuration", return_value=get_configuration_response
    )
    configuration_handler = ComponentConfigurationHandler(ipc_client)
    configuration = configuration_handler.get_configuration()
    assert mock_ipc_get_config.call_count == 1

    assert configuration.get_container_name() == "some-container-name"
    assert configuration.get_db_credentials() == ("", "")
    assert configuration.get_host_volume() == "/some/volume/"
    assert configuration.get_host_port() == "8000"


def test_configuration_set_credential_secret_config(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    get_configuration_response = GetConfigurationResponse(value={"DBCredentialSecret": "secret-arn"})
    mock_ipc_get_config = mocker.patch.object(
        GreengrassCoreIPCClientV2, "get_configuration", return_value=get_configuration_response
    )

    secret_value_reponse = GetSecretValueResponse(
        secret_value=SecretValue(
            secret_string={"postgresql_username": "this-is-a-username", "postgresql_password": "this-is-a-password"}
        )
    )
    mock_ipc_get_secret = mocker.patch.object(GreengrassCoreIPCClientV2, "get_secret_value", return_value=secret_value_reponse)
    configuration_handler = ComponentConfigurationHandler(ipc_client)

    configuration = configuration_handler.get_configuration()
    assert mock_ipc_get_config.call_count == 1
    assert mock_ipc_get_secret.call_count == 1

    assert configuration.get_container_name() == "greengrass_postgresql"
    assert configuration.get_db_credentials() == ("this-is-a-username", "this-is-a-password")
    assert configuration.get_host_volume() == consts.DEFAULT_HOST_VOLUME
    assert configuration.get_host_port() == consts.DEFAULT_HOST_PORT
