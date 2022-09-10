from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration import ComponentConfigurationHandler


def __main__():
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_handler = ComponentConfigurationHandler(ipc_client)
    configuration_handler.subscribe_to_configuration_updates()

    # Will the start the docker container with the latest component configuration
