import pytest
import src.constants as consts
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2
from awsiot.greengrasscoreipc.model import GetConfigurationResponse, GetSecretValueResponse, SecretValue
from src.configuration_handler import ComponentConfigurationIPCHandler


def test_configuration_default_values(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mock_ipc_client = GreengrassCoreIPCClientV2()
    configuration_handler = ComponentConfigurationIPCHandler(mock_ipc_client)

    configuration = configuration_handler.get_configuration()
    assert configuration.get_container_name() == "greengrass_postgresql"
    assert configuration.get_db_credentials() == ("", "")
    assert configuration.get_host_volume() == consts.DEFAULT_HOST_VOLUME
    assert configuration.get_host_port() == consts.DEFAULT_HOST_PORT


def test_configuration_set_container_config(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_response = GetConfigurationResponse(
        value={"ContainerMapping": {"HostPort": "8000", "HostVolume": "/some/volume/", "ContainerName": "some-container-name"}}
    )
    mock_ipc_get_config = mocker.patch.object(
        GreengrassCoreIPCClientV2, "get_configuration", return_value=configuration_response
    )
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    configuration = configuration_handler.get_configuration()
    assert mock_ipc_get_config.call_count == 1

    assert configuration.get_container_name() == "some-container-name"
    assert configuration.get_db_credentials() == ("", "")
    assert configuration.get_host_volume() == "/some/volume/"
    assert configuration.get_host_port() == "8000"


def test_configuration_set_credential_secret_config(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_response = GetConfigurationResponse(value={"DBCredentialSecret": "secret-arn"})
    mock_ipc_get_config = mocker.patch.object(
        GreengrassCoreIPCClientV2, "get_configuration", return_value=configuration_response
    )

    secret_value_reponse = GetSecretValueResponse(
        secret_value=SecretValue(
            secret_string='{"POSTGRES_USER": "this-is-a-username", "POSTGRES_PASSWORD": "Thi5-is-@-password"}'
        )
    )
    mock_ipc_get_secret = mocker.patch.object(GreengrassCoreIPCClientV2, "get_secret_value", return_value=secret_value_reponse)
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)

    configuration = configuration_handler.get_configuration()
    assert mock_ipc_get_config.call_count == 1
    assert mock_ipc_get_secret.call_count == 1

    assert configuration.get_container_name() == "greengrass_postgresql"
    assert configuration.get_db_credentials() == ("this-is-a-username", "Thi5-is-@-password")
    assert configuration.get_host_volume() == consts.DEFAULT_HOST_VOLUME
    assert configuration.get_host_port() == consts.DEFAULT_HOST_PORT


def test_configuration_set_credential_missing_credentials(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_response = GetConfigurationResponse(value={"DBCredentialSecret": "secret-arn"})
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=configuration_response)

    secret_value_reponse = GetSecretValueResponse(
        secret_value=SecretValue(
            secret_string='{"POSTGRES_USERNAME": "this-is-a-username", "POSTGRES_PASSWORD": "Thi5-is-@-password"}'
        )
    )
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_secret_value", return_value=secret_value_reponse)
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    with pytest.raises(Exception) as err:
        configuration_handler.get_configuration()
    assert (
        "Missing postgresql credentials. Please provide a valid secret with postgresql username (POSTGRES_USER) and password"
        " (POSTGRES_PASSWORD) credentials"
        in err.value.args[0]
    )


@pytest.mark.parametrize(
    "invalid_password",
    ["!Lessthan16", "!7nouppercasebut16char", "!7NOLOWERCASEBUT16CHAR", "NOdigit!nThepassword", "No5specialCharacter"],
)
def test_configuration_set_credential_invalid_password(mocker, invalid_password):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_response = GetConfigurationResponse(value={"DBCredentialSecret": "secret-arn"})
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=configuration_response)
    secret_str = '{"POSTGRES_USER": "this-is-a-username", "POSTGRES_PASSWORD": "' + invalid_password + '"}'
    secret_value_reponse = GetSecretValueResponse(secret_value=SecretValue(secret_string=secret_str))
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_secret_value", return_value=secret_value_reponse)
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    with pytest.raises(Exception) as err:
        configuration_handler.get_configuration()
    assert (
        "Invalid postgresql password. Password must be at least 16 character long with uppercase and lowercase letters,"
        " numbers, and special characters."
        in err.value.args[0]
    )


def test_configuration_set_conf_volumes(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_response = GetConfigurationResponse(
        value={
            "ConfigurationFiles": {
                "postgresql.conf": "/path/to/custom/postgresql.conf",
                "unsupported.conf": "/path/to/custom/unsupported.conf",
                "pg_hba.conf": "conf",
                "pg_ident.conf": "conf",
            }
        }
    )
    mocker.patch.object(GreengrassCoreIPCClientV2, "get_configuration", return_value=configuration_response)

    mocker.patch("pathlib.Path.is_file", return_value=True)
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    pg_conf_files = configuration_handler.get_configuration().get_pg_config_files()
    assert len(pg_conf_files) == 3
    assert "postgresql.conf" in pg_conf_files
    assert "pg_hba.conf" in pg_conf_files
    assert "pg_ident.conf" in pg_conf_files
