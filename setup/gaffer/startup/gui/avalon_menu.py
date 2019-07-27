# Add Avalon Menu entries to GafferUI
# See: http://www.gafferhq.org/documentation/0.53.0.0/Tutorials/Scripting
# /AddingAMenuItem/index.html
import GafferUI


def _install_avalon_menu():

    from avalon.tools import (
        creator,
        cbloader,
        publish,
        cbsceneinventory,
        workfiles
    )

    menu = GafferUI.ScriptWindow.menuDefinition(application)
    menu.append("/Avalon/Create...",
                {"command": lambda *args: creator.show()})
    menu.append("/Avalon/Load...",
                {"command": lambda *args: cbloader.show(use_context=True)})
    menu.append("/Avalon/Publish...",
                {"command": lambda *args: publish.show()})
    menu.append("/Avalon/Manage...",
                {"command": lambda *args: cbsceneinventory.show()})

    # Divider
    menu.append("/Avalon/WorkFilesDivider",
                {"divider": True})

    menu.append("/Avalon/Work Files...",
                {"command": lambda *args: workfiles.show()})


def _install_avalon():

    from avalon import api, gaffer
    api.install(gaffer)


_install_avalon()
_install_avalon_menu()
