import datetime
import math
import inspect

from ...vendor.Qt import QtWidgets, QtCore
from ...vendor import qtawesome
from ... import io
from ... import api
from ... import pipeline

from .model import SubsetsModel, FamiliesFilterProxyModel
from .delegates import PrettyTimeDelegate, VersionDelegate
from . import lib

from ..lib import schedule


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

        # Header (filter + toggle details)
        header = QtWidgets.QHBoxLayout()

        filter = QtWidgets.QLineEdit()
        filter.setPlaceholderText("Filter subsets..")

        toggle_details = QtWidgets.QPushButton("Hide Details")
        toggle_details.setFixedWidth(100)
        toggle_details.setFixedHeight(22)

        header.addWidget(filter)
        header.addWidget(toggle_details)

        # View
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

        view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        view.setSortingEnabled(True)
        view.sortByColumn(1, QtCore.Qt.AscendingOrder)
        view.setAlternatingRowColors(True)

        # Main body (left column)
        body = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(header)
        layout.addWidget(view)

        # Details (right column)
        details = SubsetDetailsWidget()

        # Layout
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        split = QtWidgets.QSplitter()
        split.setStyleSheet("QSplitter { border: 0px; }")
        split.addWidget(body)
        split.addWidget(details)
        split.setSizes([800, 200])
        split.setCollapsible(1, False)
        layout.addWidget(split)

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
        self.details = details
        self.toggle_details = toggle_details

        # settings and connections
        self.proxy.setSourceModel(self.model)
        self.proxy.setDynamicSortFilter(True)
        self.proxy.setFilterCaseSensitivity(QtCore.Qt.CaseInsensitive)

        self.view.setModel(self.family_proxy)
        self.view.customContextMenuRequested.connect(self.on_context_menu)

        selection = view.selectionModel()
        selection.selectionChanged.connect(self.active_changed)

        version_delegate.version_changed.connect(self.version_changed)

        self.filter.textChanged.connect(self.proxy.setFilterRegExp)
        self.active_changed.connect(self.on_versionschanged)
        self.version_changed.connect(self.on_versionschanged)
        self.toggle_details.clicked.connect(self.on_toggle_details)

        self.model.refresh()

        # Expose this from the widget as a method
        self.set_family_filters = self.family_proxy.setFamiliesFilter

    def set_asset(self, asset_id):

        # Clear previous
        self.model.clear()

        # Force a refresh on details widget (not sure why needed)
        # TODO: Figure out how to avoid needing this here
        self.on_versionschanged()

        if not asset_id:
            return

        self.model.set_asset(asset_id)

        # Enforce the columns to fit the data (purely cosmetic)
        rows = self.model.rowCount(QtCore.QModelIndex())
        for i in range(rows):
            self.view.resizeColumnToContents(i)

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
            version_id = node["version_document"]["_id"]
            representation = io.find_one({"type": "representation",
                                          "name": representation_name,
                                          "parent": version_id})
            if not representation:
                self.echo("Subset '{}' has no representation '{}'".format(
                          node["subset"],
                          representation_name
                          ))
                continue

            try:
                api.load(Loader=loader, representation=representation)
            except pipeline.IncompatibleLoaderError as exc:
                self.echo(exc)
                continue

    def echo(self, message):
        print(message)

    def on_versionschanged(self, *args):
        self.echo("Fetching version..")
        schedule(self._versionschanged, 150, channel="mongo")

    def _versionschanged(self):

        selection = self.view.selectionModel()

        # Active must be in the selected rows otherwise we
        # assume it's not actually an "active" current index.
        version = None
        active = selection.currentIndex()
        if active:
            rows = selection.selectedRows(column=active.column())
            if active in rows:
                node = active.data(self.model.NodeRole)
                version = node['version_document']['_id']

        self.details.set_version(version)

    def on_toggle_details(self):

        state = not self.details.isHidden()

        if not state:
            self.details.show()
            self.toggle_details.setText("Hide Details")
        else:
            self.details.hide()
            self.toggle_details.setText("Show Details")


class VersionHistory(QtWidgets.QListWidget):
    """A list of a subset's version history"""
    def __init__(self):
        super(VersionHistory, self).__init__()
        self.setSpacing(1)

        # For now disable any selections
        self.setSelectionMode(self.NoSelection)

    def set_subset(self, subset):
        self.clear()

        versions = io.find({"type": "version",
                            "parent": subset},
                           sort=[("name", -1)])
        for version in versions:
            self._add_version(version)

    def _add_version(self, version):
        """

        --------------
        version (date)
        user: comment
        --------------
        """

        widget = QtWidgets.QWidget()
        widget.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        widget.setContentsMargins(0, 0, 0, 0)
        widget.setObjectName("frame")
        widget.setStyleSheet("#frame { "
                             "margin: 2px; "
                             "background-color: rgba(45, 45, 45, 0.9); "
                             "}")

        item = QtWidgets.QListWidgetItem(self)
        self.addItem(item)
        self.setItemWidget(item, widget)

        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        widget.setLayout(layout)

        header = QtWidgets.QHBoxLayout()

        version_name = "Version {0:03d}".format(version['name'])
        version_data = version["data"]

        created = version_data["time"]
        created = datetime.datetime.strptime(created, "%Y%m%dT%H%M%SZ")
        created = datetime.datetime.strftime(created, "%Y-%m-%d %H:%M")

        comment = version_data.get("comment") or "-"
        if "author" in version_data:
            comment = "<i>{0}</i>: ".format(version_data["author"]) + comment

        # Version label
        version_label = QtWidgets.QLabel(version_name)
        version_label.setStyleSheet("QLabel { "
                                    "font-size: 11px; "
                                    "font-weight: bold; "
                                    "color: #DDDDDD; "
                                    "background: transparent; "
                                    "}")
        version_label.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                    QtWidgets.QSizePolicy.Fixed)
        version_label.setAutoFillBackground(False)

        # Date label
        date_label = QtWidgets.QLabel(created)
        date_label.setStyleSheet("QLabel { "
                                 "font-size: 10px; "
                                 "background: transparent; "
                                 "}")
        date_label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        date_label.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                 QtWidgets.QSizePolicy.Fixed)
        date_label.setAutoFillBackground(False)

        # Comment label
        comment_label = QtWidgets.QLabel(comment)
        comment_label.setAlignment(QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        comment_label.setAutoFillBackground(False)
        comment_label.setStyleSheet("QLabel { background: transparent; }")
        comment_label.setWordWrap(True)

        header.addWidget(version_label)
        header.addWidget(date_label)
        layout.addLayout(header)
        layout.addWidget(comment_label)

        item.setSizeHint(QtCore.QSize(0, 55))


class SubsetDetailsWidget(QtWidgets.QWidget):
    """A Widget that display information about a specific version"""
    def __init__(self, parent=None):
        super(SubsetDetailsWidget, self).__init__(parent=parent)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        stack = QtWidgets.QStackedWidget()
        layout.addWidget(stack)

        self.setMinimumWidth(220)

        deselected = QtWidgets.QLabel("Select a subset for details.")
        deselected.setAlignment(QtCore.Qt.AlignCenter)
        details = QtWidgets.QWidget(self)

        stack.addWidget(deselected)
        stack.addWidget(details)

        details_layout = QtWidgets.QVBoxLayout(details)
        details_layout.setContentsMargins(0, 0, 0, 0)
        thumb = QtWidgets.QLabel()
        thumb.setAlignment(QtCore.Qt.AlignCenter)
        thumb.setFixedHeight(50)
        thumb_default = qtawesome.icon("fa.file-o",
                                       color="white").pixmap(50, 50)
        thumb.setPixmap(thumb_default)

        label = QtWidgets.QLabel("Label")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("QLabel{ font-size: 14px; font-weight: bold; }")

        history = VersionHistory()

        details_layout.addWidget(thumb, QtCore.Qt.AlignCenter)
        details_layout.addWidget(label)
        details_layout.addWidget(history)

        self.stack = stack

        self.thumb_default = thumb_default
        self.widgets = {
            "label": label,
            "thumb": thumb,
            "history": history
        }

    def set_version(self, version_id):

        if not version_id:
            print("No version selected.")
            self.stack.setCurrentIndex(0)
            return

        self.stack.setCurrentIndex(1)

        version = io.find_one({"_id": version_id, "type": "version"})
        assert version, "Not a valid version id"

        subset = io.find_one({"_id": version['parent'], "type": "subset"})
        assert subset, "No valid subset parent for version"

        # Get Family label and icon
        families = version["data"].get("families")
        if families:
            primary_family = families[0]
        else:
            primary_family = version["data"].get("family", "unknown")

        family = lib.get(lib.FAMILY_CONFIG, primary_family)
        icon = family.get("icon")
        if icon:
            pixmap = icon.pixmap(50, 50)
        else:
            pixmap = self.thumb_default

        self.widgets["label"].setText(subset['name'])
        self.widgets["thumb"].setPixmap(pixmap)
        self.widgets["history"].set_subset(subset["_id"])


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
