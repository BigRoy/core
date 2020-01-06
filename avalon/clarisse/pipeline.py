import sys
import importlib
import logging
from collections import OrderedDict

import pyblish.api
import ix

from ..pipeline import AVALON_CONTAINER_ID

self = sys.modules[__name__]
self._menu = "Avalon>"
self._menu_callbacks = {}    # store custom menu callbacks, see _install_menu


log = logging.getLogger(__name__)


def ls():
    """Currently yields references only"""
    contexts = ix.api.OfContextSet()
    ix.application.get_factory().get_root().resolve_all_contexts(contexts)
    for context in contexts:
        if context.is_reference() and not context.is_disabled():
            container = parse_container(context)
            if container:
                yield container


def find_host_config(config):
    config_name = config.__name__
    try:
        config = importlib.import_module(config_name + ".clarisse")
    except ImportError as exc:
        print(exc)
        config = None
    return config


def install(config):
    """Install clarisse-specific functionality of avalon-core.

    This function is called automatically on calling `api.install(clarisse)`.

    """

    # Ensure QApplication runs with Clarisse helper.
    from avalon.vendor.Qt import QtWidgets
    import pyqt_clarisse
    app = QtWidgets.QApplication.instance()
    if not app:
        print("Starting QApplication with pyqt_clarisse helper..")
        app = QtWidgets.QApplication([])
        pyqt_clarisse.exec_(app)

    pyblish.api.register_host("clarisse")

    _install_menu()

    # Trigger install on the config's "clarisse" package
    config = find_host_config(config)
    if hasattr(config, "install"):
        config.install()


def _install_menu():
    """Install Avalon menu into Clarisse main menu"""

    from ..tools import (
        creator,
        loader,
        publish,
        sceneinventory,
        workfiles
    )

    def add_command_callback(menu,
                             name,
                             callback):
        """Helper function to add menu command with Python callback

        This allows us to avoid passing all commands as string script, like:
            menu.add_command_as_script(
                "ScriptingPython",
                "Menu>Command",
                "import avalon.tools.creator as tool; tool.show()"
            )

        """

        # Store the callback
        self._menu_callbacks[name] = callback

        # Build the call by name (escape any extra ' in name)
        cmd = (
            "import avalon.clarisse.pipeline; "
            "avalon.clarisse.pipeline._menu_callbacks['{name}']()"
        ).format(name=name.replace("'", "\'"))
        menu.add_command_as_script("ScriptingPython",
                                   name,
                                   cmd)

    menu = ix.application.get_main_menu()

    # Build top menu entry
    menu_name = self._menu   # get menu name
    menu.add_command(menu_name)

    # Add commands
    add_command_callback(menu, menu_name + "Create...",
                         callback=lambda: creator.show())
    add_command_callback(menu, menu_name + "Load...",
                         callback=lambda: loader.show(use_context=True))
    add_command_callback(menu, menu_name + "Publish...",
                         callback=lambda: publish.show())
    add_command_callback(menu, menu_name + "Manage...",
                         callback=lambda: sceneinventory.show())

    menu.add_command(menu_name + "{Work}")

    add_command_callback(menu, menu_name + "Work Files",
                         callback=lambda: workfiles.show())

    menu.add_command(menu_name + "{Utilities}")

    menu.add_command(menu_name + "Reset resolution")
    menu.add_command(menu_name + "Reset frame range")


def _uninstall_menu():
    """Uninstall Avalon menu from Clarisse main menu"""

    main_menu = ix.application.get_main_menu()
    main_menu.remove_all_commands(self._menu)

    # Remove all saved menu callbacks
    self._menu_callbacks = {}


def uninstall(config):
    """Uninstall clarisse-specific functionality of avalon-core.

    This function is called automatically on calling `api.uninstall(clarisse)`.

    """
    _uninstall_menu()

    config = find_host_config(config)
    if hasattr(config, "uninstall"):
        config.uninstall()

    pyblish.api.deregister_host("clarisse")


def imprint(node, data, group="avalon"):
    """Store string attributes with value on a node

    Args:
        node (framework.PyOfObject): The node to imprint data on.
        data (dict): Key value pairs of attributes to create.
        group (str): The Group to add the attributes to.

    Returns:
        None

    """
    for attr, value in data.items():

        # Create the attribute
        node.add_attribute(attr,
                           ix.api.OfAttr.TYPE_STRING,
                           ix.api.OfAttr.CONTAINER_SINGLE,
                           ix.api.OfAttr.VISUAL_HINT_DEFAULT,
                           group)

        # Set the attribute's value
        node.get_attribute(attr)[0] = str(value)


def imprint_container(node, name, namespace, context, loader):
    """Imprint `node` with container metadata.

    Arguments:
        node (framework.PyOfObject): The node to containerise.
        name (str): Name of resulting assembly
        namespace (str): Namespace under which to host container
        context (dict): Asset information
        loader (str): Name of loader used to produce this container.

    Returns:
        None

    """

    data = [
        ("schema", "avalon-core:container-2.0"),
        ("id", AVALON_CONTAINER_ID),
        ("name", name),
        ("namespace", namespace),
        ("loader", loader),
        ("representation", context["representation"]["_id"])
    ]

    # We use an OrderedDict to make sure the attributes
    # are always created in the same order. This is solely
    # to make debugging easier when reading the values in
    # the attribute editor.
    imprint(node, OrderedDict(data))


def parse_container(node):
    """Return the container node's full container data.

    Args:
        node (framework.PyOfObject: A node to parse as container.

    Returns:
        dict: The container schema data for this container node.

    """

    # If not all required data return None
    required = ['id', 'schema', 'name',
                'namespace', 'loader', 'representation']
    if not all(node.attribute_exists(attr) for attr in required):
        return

    data = {attr: node.get_attribute(attr)[0] for attr in required}

    # Store the node's name
    data["objectName"] = node.get_full_name()

    # Store reference to the node object
    data["node"] = node

    return data
