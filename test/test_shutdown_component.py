import docker
from docker.models.containers import Container, ContainerCollection
from src.shutdown_component import cleanup_container, main


def test_remove_container(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mocker.patch("src.shutdown_component", return_value=None)
    mocker.patch("docker.DockerClient.containers", return_value=ContainerCollection())
    mocker.patch("src.shutdown_component.remove_container", return_value=None)
    mocker.patch.object(docker.DockerClient.containers, "get", return_value=Container())
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    cleanup_container(docker.DockerClient, "some-container")
    assert mock_remove_container.called
    assert mock_stop_container.called


def test_remove_container_no_container(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mocker.patch("src.shutdown_component", return_value=None)
    mocker.patch("docker.DockerClient.containers", return_value=ContainerCollection())
    mocker.patch.object(docker.DockerClient.containers, "get", side_effect=Exception("Container does not exist"))
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    cleanup_container(docker.DockerClient, "some-container")

    assert not mock_remove_container.called
    assert not mock_stop_container.called


def test_shutdown_component_no_container(mocker):
    mocker.patch("awsiot.greengrasscoreipc", return_value=None)
    mocker.patch("src.configuration_handler", return_value=None)
    mocker.patch("docker.DockerClient", return_value=None)
    mock_remove_container = mocker.patch.object(Container, "remove", return_value=None)
    mock_stop_container = mocker.patch.object(Container, "stop", return_value=None)
    mock_cleanup_container = mocker.patch("src.shutdown_component.cleanup_container", return_value=None)
    main()

    assert mock_cleanup_container.called
    assert not mock_remove_container.called
    assert not mock_stop_container.called
