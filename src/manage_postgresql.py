from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration_handler import ComponentConfigurationIPCHandler

if __name__ == "__main__":
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    configuration_handler.subscribe_to_configuration_updates()

    # Will the start the docker container with the latest component configuration
