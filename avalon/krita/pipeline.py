import sys
import importlib

from pyblish import api as pyblish
from .. import api as avalon
from ..vendor.Qt import QtCore, QtWidgets

import krita


self = sys.modules[__name__]
self._menu = "AvalonKritaMenu"  # Unique name of menu
self._parent = None             # Main Window


def install(config):
    """Install Krita-specific functionality of avalon-core.

    This function is called automatically on calling `api.install(maya)`.

    """

    pyblish.register_host("krita")

    _install_menu()

    config = find_host_config(config)
    if hasattr(config, "install"):
        config.install()


def uninstall(config):

    config = find_host_config(config)
    if hasattr(config, "uninstall"):
        config.uninstall()

    _uninstall_menu()

    pyblish.deregister_host("krita")


def _get_main_window():
    """Return Krita QMainWindow instance"""

    if self._parent:
        # If cached, return it directly
        return self._parent

    app = QtWidgets.QApplication.instance()
    for widget in app.topLevelWidgets():
        if widget.objectName() == "MainWindow#1":
            self._parent = widget
            return widget


def _install_menu():

    from ..tools import creator, loader, publish, sceneinventory, workfiles

    main_window = _get_main_window()
    menubar = main_window.menuBar()
    menu = menubar.addMenu("Avalon")
    menu.setObjectName(self._menu)

    action = menu.addAction("Create..")
    action.triggered.connect(lambda: creator.show(parent=main_window))

    action = menu.addAction("Load..")
    action.triggered.connect(lambda: loader.show(use_context=True,
                                                 parent=main_window))

    action = menu.addAction("Publish..")
    action.triggered.connect(lambda: publish.show())

    action = menu.addAction("Manage..")
    action.triggered.connect(lambda: sceneinventory.show(parent=main_window))

    menu.addSeparator()
    action = menu.addAction("Work Files")
    action.triggered.connect(lambda: workfiles.show(parent=main_window))


def _uninstall_menu():

    main_window = _get_main_window()
    if not main_window:
        return

    menubar = main_window.menuBar()
    menu = menubar.findChild(self._menu)
    if menu:
        menu_action = menu.menuAction()
        menubar.removeAction(menu_action)
        menu.deleteLater()


def ls():
    """List containers from active Krita document

    This is the host-equivalent of api.ls(), but instead of listing
    assets on disk, it lists assets already loaded in Fusion; once loaded
    they are called 'containers'

    """

    document = krita.Krita.instance().activeDocument()
    if not document:
        return

    # todo: Implement ls() and maybe parse_container()?
    raise NotImplementedError("Not implemented.")


def find_host_config(config):
    try:
        config = importlib.import_module(config.__name__ + ".krita")
    except ImportError as exc:
        if str(exc) != "No module name {}".format(config.__name__ + ".krita"):
            raise
        config = None

    return config
