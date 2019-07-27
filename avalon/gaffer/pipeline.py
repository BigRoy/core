import importlib
import pyblish.api


def install(config):
    """Setup integration
    Register plug-ins and integrate into the host

    """

    # print("Registering callbacks")
    # _register_callbacks()

    pyblish.api.register_host("gaffer")

    config = find_host_config(config)
    if hasattr(config, "install"):
        config.install()


def uninstall(config):
    """Uninstall Houdini-specific functionality of avalon-core.

    This function is called automatically on calling `api.uninstall()`.

    Args:
        config: configuration module

    """

    config = find_host_config(config)
    if hasattr(config, "uninstall"):
        config.uninstall()

    pyblish.api.deregister_host("gaffer")


def find_host_config(config):
    try:
        config = importlib.import_module(config.__name__ + ".gaffer")
    except ImportError as exc:
        if str(exc) != "No module name {}".format(config.__name__ + ".gaffer"):
            raise
        config = None

    return config


def ls():
    pass


def containerise():
    pass
