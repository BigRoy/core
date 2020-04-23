from ...vendor.Qt import QtWidgets, QtCore, QtGui
from ...vendor import qtawesome
from ... import io, api

from ..widgets import AssetWidget
from ..models import TasksModel, TreeModel, Item, ActionModel, ProjectsModel

from . import lib


class ProjectBar(QtWidgets.QWidget):

    project_changed = QtCore.Signal(int)

    def __init__(self, parent=None):
        super(ProjectBar, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)

        self.view = QtWidgets.QComboBox()
        self.model = ProjectsModel()
        self.view.setModel(self.model)
        self.view.setRootModelIndex(QtCore.QModelIndex())

        layout.addWidget(self.view)

        # Initialize
        self.model.refresh()

        # Set current project
        project = api.Session["AVALON_PROJECT"]
        index = self.view.findText(project)
        if index >= 0:
            self.view.setCurrentIndex(index)

        # Signals
        self.view.currentIndexChanged.connect(self.project_changed)

        self.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding,
                           QtWidgets.QSizePolicy.Maximum)

    def get_current_project(self):
        return self.view.currentText()

    def set_project(self, project):

        index = self.view.findText(project)
        if index >= 0:
            self.view.setCurrentIndex(index)


class ActionBar(QtWidgets.QWidget):
    """Launcher interface"""

    action_clicked = QtCore.Signal(object)

    def __init__(self, parent=None):
        super(ActionBar, self).__init__(parent)

        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 0, 8, 0)

        view = QtWidgets.QListView()
        view.setViewMode(QtWidgets.QListView.IconMode)
        view.setResizeMode(QtWidgets.QListView.Adjust)
        view.setSelectionMode(QtWidgets.QListView.NoSelection)
        #view.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        #view.setFlow(QtWidgets.QListView.LeftToRight)
        view.setWrapping(True)
        view.setGridSize(QtCore.QSize(80, 75))
        view.setIconSize(QtCore.QSize(30, 30))
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

        model = ActionModel()
        view.setModel(model)

        layout.addWidget(view)

        self.model = model
        self.view = view

        self.set_row_height(1)

        view.clicked.connect(self.on_clicked)

    def set_row_height(self, rows):
        self.setMinimumHeight(rows * 75)

    def on_clicked(self, index):

        if index.isValid():
            item = index.data(self.model.ItemRole)
            Action = item["action"]
            self.action_clicked.emit(Action)


class TasksWidget(QtWidgets.QWidget):
    """Widget showing active Tasks"""

    task_changed = QtCore.Signal()

    def __init__(self):
        super(TasksWidget, self).__init__()

        view = QtWidgets.QTreeView()
        view.setIndentation(0)
        model = TasksModel()
        view.setModel(model)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(view)

        # Hide the default tasks "count" as we don't need that data here.
        view.setColumnHidden(1, True)

        selection = view.selectionModel()
        selection.selectionChanged.connect(self.task_changed)

        self.models = {
            "tasks": model
        }

        self.widgets = {
            "view": view,
        }

        self._last_selected_task = None

    def set_asset(self, asset_id):

        if asset_id is None:
            # Asset deselected
            self.models["tasks"].set_assets([])
            return

        # Try and preserve the last selected task and reselect it
        # after switching assets. If there's no currently selected
        # asset keep whatever the "last selected" was prior to it.
        current = self.get_current_task()
        if current:
            self._last_selected_task = current

        self.models["tasks"].set_assets([asset_id])

        if self._last_selected_task:
            self.select_task(self._last_selected_task)

        # Force a task changed emit.
        self.task_changed.emit()

    def select_task(self, task):
        """Select a task by name.

        If the task does not exist in the current model then selection is only
        cleared.

        Args:
            task (str): Name of the task to select.

        """

        # Clear selection
        view = self.widgets["view"]
        model = view.model()
        selection_model = view.selectionModel()
        selection_model.clearSelection()

        # Select the task
        mode = selection_model.Select | selection_model.Rows
        for row in range(model.rowCount(QtCore.QModelIndex())):
            index = model.index(row, 0, QtCore.QModelIndex())
            name = index.data(QtCore.Qt.DisplayRole)
            if name == task:
                selection_model.select(index, mode)

                # Set the currently active index
                view.setCurrentIndex(index)

    def get_current_task(self):
        """Return name of task at current index (selected)

        Returns:
            str: Name of the current task.

        """
        view = self.widgets["view"]
        index = view.currentIndex()
        index = index.sibling(index.row(), 0)  # ensure column zero for name

        selection = view.selectionModel()
        if selection.isSelected(index):
            # Ignore when the current task is not selected as the "No task"
            # placeholder might be the current index even though it's
            # disallowed to be selected. So we only return if it is selected.
            return index.data(QtCore.Qt.DisplayRole)


class ActionHistory(QtWidgets.QPushButton):

    trigger_history = QtCore.Signal(tuple)

    def __init__(self, parent=None):
        super(ActionHistory, self).__init__(parent=parent)

        self.max_history = 15

        self.setFixedWidth(25)
        self.setFixedHeight(25)

        self.setIcon(qtawesome.icon("fa.history", color="#CCCCCC"))
        self.setIconSize(QtCore.QSize(15, 15))

        self._history = []
        self.clicked.connect(self.show_history)

    def show_history(self):
        # Show history popup

        if not self._history:
            return

        cursor = QtGui.QCursor()
        point = cursor.pos()

        widget = QtWidgets.QListWidget()
        widget.setSelectionMode(widget.NoSelection)

        widget.setStyleSheet("""
        * {
            font-family: "Courier New";
        }
        """)

        largest_label_num_chars = 0
        largest_action_label = max(len(x[0].label) for x in self._history)
        print(largest_action_label)

        action_session_role = QtCore.Qt.UserRole + 1

        for action, session in reversed(self._history):
            project = session.get("AVALON_PROJECT")
            asset = session.get("AVALON_ASSET")
            task = session.get("AVALON_TASK")
            breadcrumb = " > ".join(x for x in [project, asset, task] if x)

            m = "{{action:{0}}} | {{breadcrumb}}".format(largest_action_label)
            label = m.format(action=action.label, breadcrumb=breadcrumb)

            icon_name = action.icon
            color = action.color or "white"
            icon = qtawesome.icon("fa.%s" % icon_name, color=color)
            item = QtWidgets.QListWidgetItem(icon, label)
            item.setData(action_session_role, (action, session))

            largest_label_num_chars = max(largest_label_num_chars, len(label))

            widget.addItem(item)

        # Show history
        width = 40 + (largest_label_num_chars * 7)  # padding + icon + text
        entry_height = 21
        height = entry_height * len(self._history)

        dialog = QtWidgets.QDialog(parent=self)
        dialog.setWindowTitle("Action History")
        dialog.setWindowFlags(QtCore.Qt.FramelessWindowHint |
                              QtCore.Qt.Popup)
        dialog.setSizePolicy(QtWidgets.QSizePolicy.Ignored,
                             QtWidgets.QSizePolicy.Ignored)

        layout = QtWidgets.QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(widget)

        def on_clicked(index):
            data = index.data(action_session_role)
            self.trigger_history.emit(data)
            dialog.close()

        widget.clicked.connect(on_clicked)

        dialog.setGeometry(point.x() - width,
                           point.y() - height,
                           width,
                           height)
        dialog.exec_()

        self.widget_popup = widget

    def add_action(self, action, session):
        import copy

        key = (action, copy.deepcopy(session))

        # Remove entry if already exists
        try:
            index = self._history.index(key)
            self._history.pop(index)
        except ValueError:
            pass

        self._history.append(key)

        # Slice the end of the list if we exceed the max history
        if len(self._history) > self.max_history:
            self._history = self._history[-self.max_history:]

    def clear_history(self):
        self._history[:] = []


class SlidePageWidget(QtWidgets.QStackedWidget):
    """Stacked widget that nicely slides between its pages"""

    directions = {
        "left": QtCore.QPoint(-1, 0),
        "right": QtCore.QPoint(1, 0),
        "up": QtCore.QPoint(0, 1),
        "down": QtCore.QPoint(0, -1)
    }

    def slide_view(self, index, direction="right"):

        if self.currentIndex() == index:
            return

        offset = self.directions.get(direction)
        assert offset is not None, "invalid slide direction: %s" % (direction,)

        width = self.frameRect().width()
        height = self.frameRect().height()
        offset = QtCore.QPoint(offset.x() * width, offset.y() * height)

        new_page = self.widget(index)
        new_page.setGeometry(0, 0, width, height)
        curr_pos = new_page.pos()
        new_page.move(curr_pos + offset)
        new_page.show()
        new_page.raise_()

        current_page = self.currentWidget()

        b_pos = QtCore.QByteArray(b"pos")

        anim_old = QtCore.QPropertyAnimation(current_page, b_pos, self)
        anim_old.setDuration(250)
        anim_old.setStartValue(curr_pos)
        anim_old.setEndValue(curr_pos - offset)
        anim_old.setEasingCurve(QtCore.QEasingCurve.OutQuad)

        anim_new = QtCore.QPropertyAnimation(new_page, b_pos, self)
        anim_new.setDuration(250)
        anim_new.setStartValue(curr_pos + offset)
        anim_new.setEndValue(curr_pos)
        anim_new.setEasingCurve(QtCore.QEasingCurve.OutQuad)

        anim_group = QtCore.QParallelAnimationGroup(self)
        anim_group.addAnimation(anim_old)
        anim_group.addAnimation(anim_new)

        def slide_finished():
            self.setCurrentWidget(new_page)

        anim_group.finished.connect(slide_finished)
        anim_group.start()
