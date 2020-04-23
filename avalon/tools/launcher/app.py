import sys
import copy

from ...vendor.Qt import QtWidgets, QtCore, QtGui
from ... import io, api, style

from .. import lib as tools_lib
from ..widgets import AssetWidget

from .widgets import (
    ProjectBar, ActionBar, TasksWidget, ActionHistory, SlidePageWidget
)

module = sys.modules[__name__]
module.window = None


class ProjectsPanel(QtWidgets.QWidget):
    """Projects Page"""

    project_clicked = QtCore.Signal(str)

    def __init__(self, parent=None):
        super(ProjectsPanel, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)

        from ..models import ProjectsModel

        view = QtWidgets.QListView()
        view.setViewMode(QtWidgets.QListView.IconMode)
        view.setResizeMode(QtWidgets.QListView.Adjust)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        view.setWrapping(True)
        view.setGridSize(QtCore.QSize(151, 90))
        view.setIconSize(QtCore.QSize(50, 50))
        view.setSpacing(0)
        view.setWordWrap(True)

        view.setStyleSheet("""
        QListView {
            font-size: 11px;
            border: 0px;
            padding: 0px;
            margin: 0px;
            
        }
        
        QListView::item  {
            margin-top: 6px;
            /* Won't work without borders set */
            border: 0px;
        }
        
        /* For icon only */
        QListView::icon {
            top: 3px;
        }
        """)
        model = ProjectsModel()
        model.refresh()
        view.setModel(model)

        layout.addWidget(view)

        view.clicked.connect(self.on_clicked)

    def on_clicked(self, index):

        if index.isValid():
            project = index.data(QtCore.Qt.DisplayRole)
            self.project_clicked.emit(project)


class AssetsPanel(QtWidgets.QWidget):
    """Assets page"""

    back_clicked = QtCore.Signal()

    def __init__(self, parent=None):
        super(AssetsPanel, self).__init__(parent=parent)

        # project bar
        project_bar = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(project_bar)
        layout.setSpacing(4)
        back = QtWidgets.QPushButton("<")
        back.setFixedWidth(25)
        back.setFixedHeight(23)
        projects = ProjectBar()
        projects.layout().setContentsMargins(0, 0, 0, 0)
        layout.addWidget(back)
        layout.addWidget(projects)

        # assets
        assets_widgets = QtWidgets.QWidget()
        assets_widgets.setContentsMargins(0, 0, 0, 0)
        assets_layout = QtWidgets.QVBoxLayout(assets_widgets)
        assets = AssetWidget(silo_creatable=False)
        assets_layout.addWidget(assets)

        # tasks
        tasks_widgets = TasksWidget()
        body = QtWidgets.QSplitter()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                           QtWidgets.QSizePolicy.Expanding)
        body.setOrientation(QtCore.Qt.Horizontal)
        body.addWidget(assets_widgets)
        body.addWidget(tasks_widgets)
        body.setStretchFactor(0, 100)
        body.setStretchFactor(1, 65)

        # main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(project_bar)
        layout.addWidget(body)

        self.data = {
            "model": {
                "projects": projects,
                "assets": assets,
                "tasks": tasks_widgets
            },
        }

        # signals
        projects.project_changed.connect(self.on_project_changed)
        assets.selection_changed.connect(self.asset_changed)
        back.clicked.connect(self.back_clicked)

    def set_project(self, project):
        self.data["model"]["projects"].set_project(project)

    def asset_changed(self):
        tools_lib.schedule(self.on_asset_changed, 0.05,
                           channel="assets")

    def on_project_changed(self):

        project = self.data["model"]["projects"].get_current_project()

        api.Session["AVALON_PROJECT"] = project
        self.data["model"]["assets"].refresh()

        # Force asset change callback to ensure tasks are correctly reset
        self.asset_changed()

    def on_asset_changed(self):
        """Callback on asset selection changed

        This updates the task view.

        """

        print("Asset changed..")

        tasks = self.data["model"]["tasks"]
        assets = self.data["model"]["assets"]

        asset = assets.get_active_asset_document()
        if asset:
            tasks.set_asset(asset["_id"])
        else:
            tasks.set_asset(None)

    def _get_current_session(self):

        tasks = self.data["model"]["tasks"]
        assets = self.data["model"]["assets"]

        asset = assets.get_active_asset_document()
        session = copy.deepcopy(api.Session)

        # Clear some values that we are about to collect if available
        session.pop("AVALON_SILO", None)
        session.pop("AVALON_ASSET", None)
        session.pop("AVALON_TASK", None)

        if asset:
            session["AVALON_ASSET"] = asset["name"]

            silo = asset.get("silo")
            if silo:
                session["AVALON_SILO"] = silo

            task = tasks.get_current_task()
            if task:
                session["AVALON_TASK"] = task

        return session


class Window(QtWidgets.QDialog):
    """Launcher interface"""

    def __init__(self, parent=None):
        super(Window, self).__init__(parent)

        self.setWindowTitle("Launcher")
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        project_panel = ProjectsPanel()
        asset_panel = AssetsPanel()

        pages = SlidePageWidget()
        pages.addWidget(project_panel)
        pages.addWidget(asset_panel)

        # actions
        actions = ActionBar()

        # statusbar
        statusbar = QtWidgets.QWidget()
        message = QtWidgets.QLabel()
        message.setFixedHeight(15)
        action_history = ActionHistory()
        action_history.setStatusTip("Show Action History")
        layout = QtWidgets.QHBoxLayout(statusbar)
        layout.addWidget(message)
        layout.addWidget(action_history)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(pages)
        layout.addWidget(actions)
        layout.addWidget(statusbar)
        layout.setStretch(0, 10)
        layout.setStretch(1, 3)

        self.data = {
            "label": {
                "message": message,
            },
            "pages": {
                "project": project_panel,
                "asset": asset_panel
            },
            "model": {
                "actions": actions,
                "action_history": action_history
            },
        }

        self.pages = pages

        # signals
        actions.action_clicked.connect(self.on_action_clicked)
        action_history.trigger_history.connect(self.on_history_action)
        project_panel.project_clicked.connect(self.on_project_clicked)
        asset_panel.back_clicked.connect(self.on_back_clicked)

        # Add some signals to propagate from the asset panel
        for signal in [
            asset_panel.data["model"]["projects"].project_changed,
            asset_panel.data["model"]["assets"].selection_changed,
            asset_panel.data["model"]["tasks"].task_changed
        ]:
            signal.connect(self.on_session_changed)

        self.resize(520, 740)

    def refresh(self):
        asset = self.data["pages"]["asset"]
        asset.data["model"]["assets"].refresh()
        self.refresh_actions()

    def echo(self, message):
        widget = self.data["label"]["message"]
        widget.setText(str(message))

        QtCore.QTimer.singleShot(5000, lambda: widget.setText(""))

        print(message)

    def on_project_changed(self):

        # Update the Action plug-ins available for the current project
        actions_model = self.data["model"]["actions"].model
        actions_model.discover()

    def on_session_changed(self):
        self.refresh_actions()

    def refresh_actions(self, delay=0):
        tools_lib.schedule(self.on_refresh_actions, 0.05 + delay)

    def on_project_clicked(self, project):
        print(project)
        self.pages.slide_view(1, direction="left")

        self.data["pages"]["asset"].set_project(project)

    def on_back_clicked(self):
        self.pages.slide_view(0, direction="right")
        self.refresh_actions(delay=260)

    def on_refresh_actions(self):
        session = self.get_current_session()

        actions = self.data["model"]["actions"]
        actions.model.set_session(session)
        actions.model.refresh()

    def on_action_clicked(self, action):
        self.echo("Running action: %s" % action.name)
        self.run_action(action)

    def on_history_action(self, history_data):
        action, session = history_data
        app = QtWidgets.QApplication.instance()
        modifiers = app.keyboardModifiers()

        if QtCore.Qt.ControlModifier & modifiers:
            # User is holding control
            # revert to that "session" location
            self.set_session(session)
        else:
            # Rerun the action
            self.run_action(action, session=session)

    def get_current_session(self):

        index = self.pages.currentIndex()
        if index == 1:
            # Assets page
            return self.data["pages"]["asset"]._get_current_session()

        return copy.deepcopy(api.Session)

    def run_action(self, action, session=None):

        if session is None:
            session = self.get_current_session()

        # Add to history
        history = self.data["model"]["action_history"]
        history.add_action(action, session)

        # Process the Action
        action().process(session)

    def set_session(self, session):

        panel = self.data["pages"]["asset"]

        project = session.get("AVALON_PROJECT")
        silo = session.get("AVALON_SILO")
        asset = session.get("AVALON_ASSET")
        task = session.get("AVALON_TASK")

        if project:

            # Force the "in project" view.
            self.pages.slide_view(1, direction="right")

            projects = panel.data["model"]["projects"]
            index = projects.view.findText(project)
            if index >= 0:
                projects.view.setCurrentIndex(index)

        if silo:
            panel.data["model"]["assets"].set_silo(silo)

        if asset:
            panel.data["model"]["assets"].select_assets([asset])

        if task:
            panel.on_asset_changed()     # requires a forced refresh first
            panel.data["model"]["tasks"].select_task(task)



def show(root=None, debug=False, parent=None):
    """Display Loader GUI

    Arguments:
        debug (bool, optional): Run loader in debug-mode,
            defaults to False
        parent (QtCore.QObject, optional): When provided parent the interface
            to this QObject.

    """

    try:
        module.window.close()
        del module.window
    except (RuntimeError, AttributeError):
        pass

    if debug is True:
        io.install()

    with tools_lib.application():

        import os
        up = os.path.dirname
        root = up(up(up(up(__file__))))
        icon = os.path.join(root, "res", "icons", "png", "launcher.png")
        print(icon)

        app = QtWidgets.QApplication.instance()
        app.setWindowIcon(QtGui.QIcon(icon))

        window = Window(parent)
        window.show()
        window.setStyleSheet(style.load_stylesheet())
        window.refresh()

        module.window = window


def cli(args):
    import argparse
    parser = argparse.ArgumentParser()
    #parser.add_argument("project")

    args = parser.parse_args(args)
    #project = args.project

    import launcher.actions as actions
    print("Registering default actions..")
    actions.register_default_actions()
    print("Registering config actions..")
    actions.register_config_actions()
    print("Registering environment actions..")
    actions.register_environment_actions()
    io.install()

    #api.Session["AVALON_PROJECT"] = project

    import traceback
    sys.excepthook = lambda typ, val, tb: traceback.print_last()

    show()
