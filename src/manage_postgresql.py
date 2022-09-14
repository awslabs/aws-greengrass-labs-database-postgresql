from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

from src.configuration_handler import ComponentConfigurationIPCHandler
from src.container import ContainerManagement

if __name__ == "__main__":
    ipc_client = GreengrassCoreIPCClientV2()
    configuration_handler = ComponentConfigurationIPCHandler(ipc_client)
    container_management = ContainerManagement(ipc_client)
    container_management.manage_postgresql_container(configuration_handler.get_configuration())
    # Will the start the docker container with the latest component configuration
