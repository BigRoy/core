import inspect

from ...vendor.Qt import QtWidgets, QtCore
from ...vendor import qtawesome
from ... import io
from ... import api
from ... import pipeline

from .model import SubsetsModel, VersionHistoryModel, FamiliesFilterProxyModel
from .delegates import PrettyTimeDelegate, VersionDelegate
from . import lib


class SubsetWidget(QtWidgets.QWidget):
    """A widget that lists the published subsets for an asset"""

    active_changed = QtCore.Signal()    # active index changed
    version_changed = QtCore.Signal()   # version state changed for a subset

    def __init__(self, parent=None):
        super(SubsetWidget, self).__init__(parent=parent)

        model = SubsetsModel()
        proxy = QtCore.QSortFilterProxyModel()
        family_proxy = FamiliesFilterProxyModel()
        family_proxy.setSourceModel(proxy)

        filter = QtWidgets.QLineEdit()
        filter.setPlaceholderText("Filter subsets..")

        view = QtWidgets.QTreeView()
        view.setIndentation(5)
        view.setStyleSheet("""
            QTreeView::item{
                padding: 5px 1px;
                border: 0px;
            }
        """)
        view.setAllColumnsShowFocus(True)

        # Set view delegates
        version_delegate = VersionDelegate()
        column = model.COLUMNS.index("version")
        view.setItemDelegateForColumn(column, version_delegate)

        time_delegate = PrettyTimeDelegate()
        column = model.COLUMNS.index("time")
        view.setItemDelegateForColumn(column, time_delegate)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(filter)
        layout.addWidget(view)

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        view.setSortingEnabled(True)
        view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        view.setAlternatingRowColors(True)

        self.data = {
            "delegates": {
                "version": version_delegate,
                "time": time_delegate
            }
        }

        self.proxy = proxy
        self.model = model
        self.view = view
        self.filter = filter
        self.family_proxy = family_proxy

        # settings and connections
        self.proxy.setSourceModel(self.model)
        self.proxy.setDynamicSortFilter(True)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.view.setModel(self.family_proxy)
        self.view.customContextMenuRequested.connect(self.on_context_menu)

        selection = view.selectionModel()
        selection.selectionChanged.connect(self.active_changed)

        self.filter.textChanged.connect(self.proxy.setFilterRegExp)

        self.model.refresh()

        # Expose this from the widget as a method
        self.set_family_filters = self.family_proxy.setFamiliesFilter

    def on_context_menu(self, point):

        point_index = self.view.indexAt(point)
        if not point_index.isValid():
            return

        # Get all representation->loader combinations available for the
        # index under the cursor, so we can list the user the options.
        available_loaders = api.discover(api.Loader)
        loaders = list()
        node = point_index.data(self.model.NodeRole)
        version_id = node['version_document']['_id']
        representations = io.find({"type": "representation",
                                   "parent": version_id})
        for representation in representations:
            for loader in api.loaders_from_representation(
                    available_loaders,
                    representation['_id']
            ):
                loaders.append((representation, loader))

        if not loaders:
            # no loaders available
            self.echo("No compatible loaders available for this version.")
            return

        def sorter(value):
            """Sort the Loaders by their order and then their name"""
            Plugin = value[1]
            return Plugin.order, Plugin.__name__

        # List the available loaders
        menu = QtWidgets.QMenu(self)
        for representation, loader in sorted(loaders, key=sorter):

            # Label
            label = getattr(loader, "label", None)
            if label is None:
                label = loader.__name__

            # Add the representation as suffix
            label = "{0} ({1})".format(label, representation['name'])

            action = QtWidgets.QAction(label, menu)
            action.setData((representation, loader))

            # Add tooltip and statustip from Loader docstring
            tip = inspect.getdoc(loader)
            if tip:
                action.setToolTip(tip)
                action.setStatusTip(tip)

            # Support font-awesome icons using the `.icon` and `.color`
            # attributes on plug-ins.
            icon = getattr(loader, "icon", None)
            if icon is not None:
                try:
                    key = "fa.{0}".format(icon)
                    color = getattr(loader, "color", "white")
                    action.setIcon(qtawesome.icon(key, color=color))
                except Exception as e:
                    print("Unable to set icon for loader "
                          "{}: {}".format(loader, e))

            menu.addAction(action)

        # Show the context action menu
        global_point = self.view.mapToGlobal(point)
        action = menu.exec_(global_point)
        if not action:
            return

        # Find the representation name and loader to trigger
        action_representation, loader = action.data()
        representation_name = action_representation['name']  # extension

        # Run the loader for all selected indices, for those that have the
        # same representation available
        selection = self.view.selectionModel()
        rows = selection.selectedRows(column=0)

        # Ensure active point index is also used as first column so we can
        # correctly push it to the end in the rows list.
        point_index = point_index.sibling(point_index.row(), 0)

        # Ensure point index is run first.
        try:
            rows.remove(point_index)
        except ValueError:
            pass
        rows.insert(0, point_index)

        # Trigger
        for row in rows:
            node = row.data(self.model.NodeRole)
            version_id = node['version_document']['_id']
            representation = io.find_one({"type": "representation",
                                          "name": representation_name,
                                          "parent": version_id})
            if not representation:
                self.echo("Subset '{}' has no representation '{}'".format(
                        node['subset'],
                        representation_name
                ))
                continue

            try:
                api.load(Loader=loader, representation=representation['_id'])
            except pipeline.IncompatibleLoaderError as exc:
                self.echo(exc)
                continue

    def echo(self, message):
        print(message)


class VersionsHistoryWidget(QtWidgets.QWidget):
    """

    For a subset show the history of published versions with:
        - version
        - comment
        - date
        - author

    """

    def __init__(self, parent=None):
        super(VersionsHistoryWidget, self).__init__(parent=parent)

        label = QtWidgets.QLabel("Version History")

        model = VersionHistoryModel()

        view = QtWidgets.QTreeView()
        view.setIndentation(5)
        view.setStyleSheet("""
            QTreeView::item{
                padding: 5px 1px;
                border: 0px;
            }
        """)
        view.setAlternatingRowColors(True)
        view.setAllColumnsShowFocus(True)
        view.setModel(model)

        # Stretch comment column by default since it's only field that
        # can really contain easily growing data
        header = view.header()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        view.setColumnWidth(0, 50)
        view.setColumnWidth(1, 200)
        view.setColumnWidth(2, 125)
        view.setColumnWidth(3, 80)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        layout.addWidget(view)

        self.model = model
        self.view = view

    def set_subset(self, subset_id):
        self.model.set_subset(subset_id)


class FamilyListWidget(QtWidgets.QListWidget):
    """A Widget that lists all available families"""

    NameRole = QtCore.Qt.UserRole + 1
    active_changed = QtCore.Signal(list)

    def __init__(self, parent=None):
        super(FamilyListWidget, self).__init__(parent=parent)

        multi_select = QtWidgets.QAbstractItemView.ExtendedSelection
        self.setSelectionMode(multi_select)
        self.setAlternatingRowColors(True)
        # Enable RMB menu
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_right_mouse_menu)

        self.itemChanged.connect(self._on_item_changed)

    def refresh(self):
        """Refresh the listed families.

        This gets all unique families and adds them as checkable items to
        the list.

        """

        family = io.distinct("data.family")
        families = io.distinct("data.families")
        unique_families = list(set(family + families))

        # Rebuild list
        self.blockSignals(True)
        self.clear()
        for name in sorted(unique_families):

            family = lib.get(lib.FAMILY_CONFIG, name)
            label = family.get("label", name)
            icon = family.get("icon", None)

            # TODO: This should be more managable by the artist
            # Temporarily implement support for a default state in the project
            # configuration
            state = family.get("state", True)
            state = QtCore.Qt.Checked if state else QtCore.Qt.Unchecked

            item = QtWidgets.QListWidgetItem(parent=self)
            item.setText(label)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsUserCheckable)
            item.setData(self.NameRole, name)
            item.setCheckState(state)

            if icon:
                item.setIcon(icon)

            self.addItem(item)
        self.blockSignals(False)

        self.active_changed.emit(self.get_filters())

    def get_filters(self):
        """Return the checked family items"""

        items = [self.item(i) for i in
                 range(self.count())]

        return [item.data(self.NameRole) for item in items if
                item.checkState() == QtCore.Qt.Checked]

    def _on_item_changed(self):
        self.active_changed.emit(self.get_filters())

    def _set_checkstate_all(self, state):
        _state = QtCore.Qt.Checked if state is True else QtCore.Qt.Unchecked
        self.blockSignals(True)
        for i in range(self.count()):
            item = self.item(i)
            item.setCheckState(_state)
        self.blockSignals(False)
        self.active_changed.emit(self.get_filters())

    def show_right_mouse_menu(self, pos):
        """Build RMB menu under mouse at current position (within widget)"""

        # Get mouse position
        globalpos = self.viewport().mapToGlobal(pos)

        menu = QtWidgets.QMenu(self)

        # Add enable all action
        state_checked = QtWidgets.QAction(menu, text="Enable All")
        state_checked.triggered.connect(
            lambda: self._set_checkstate_all(True))
        # Add disable all action
        state_unchecked = QtWidgets.QAction(menu, text="Disable All")
        state_unchecked.triggered.connect(
            lambda: self._set_checkstate_all(False))

        menu.addAction(state_checked)
        menu.addAction(state_unchecked)

        menu.exec_(globalpos)
