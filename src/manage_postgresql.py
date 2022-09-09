from src.configuration import ComponentConfigurationHandler


def __main__():
    configuration_handler = ComponentConfigurationHandler()
    configuration_handler.subscribe_to_configuration_updates()

    # Will the start the docker container with the latest component configuration
