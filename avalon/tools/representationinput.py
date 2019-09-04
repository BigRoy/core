from .. import io, style
from ..vendor.Qt import QtCore, QtGui, QtWidgets
from ..vendor import qtawesome as qta

from .projectmanager.model import (
    TreeModel,
    Node
)

# todo: Don't reference from cbloader.tools but somehow make reusable widgets more public

from .cbloader import lib
from .cbloader.delegates import PrettyTimeDelegate, VersionDelegate


def get_inputs(representation_id):
    representation = io.find_one({"_id": io.ObjectId(representation_id),
                                  "type": "representation"})
    return representation["data"].get("inputs", [])


def get_outputs(representation_id):
    # Note: This returns the representations, not the ids!

    representation = io.find_one({"_id": io.ObjectId(representation_id),
                                  "type": "representation"})

    # Get all representations that contain this representation in its
    # "data.inputs"
    outputs = io.find({"type": "representation",
                       "data.inputs": representation["_id"]})
    return list(outputs)


class RepresentationInputOutputModel(TreeModel):
    """A model listing the inputs/outputs for representations"""

    COLUMNS = ["label", "family", "version", "time", "author"]

    # Different modes for listing
    INPUTS = 0
    OUTPUTS = 1

    def __init__(self):
        super(RepresentationInputOutputModel, self).__init__()

        # Default mode is listing inputs
        self.mode = self.INPUTS
        self._representations = []

        self._icons = {"subset": qta.icon("fa.file-o",
                                          color=style.colors.default)}

    def load(self, representation_ids):
        """Set representation to track by their database id.

        Arguments:
            representation_ids (list): List of representation ids.

        """
        assert isinstance(representation_ids, (list, tuple))
        self._representations = representation_ids
        self.refresh()

    def set_mode(self, mode):
        self.mode = mode

    def refresh(self):

        self.clear()
        self.beginResetModel()

        representation_ids = self._representations
        for representation_id in representation_ids:
            # Populate the representations
            self._add_representation(representation_id, parent=None)

        self.endResetModel()

    def _add_representation(self, representation_id, parent):

        representation = io.find_one({"_id": io.ObjectId(representation_id),
                                      "type": "representation"})
        context = representation["context"]

        # Get the version since we want to display some information from it
        # like the specific time/date it was published.
        version = io.find_one({"_id": representation["parent"],
                               "type": "version"})

        version_data = version.get("data", dict())
        family = version_data.get("families", [None])[0]
        family_config = lib.get(lib.FAMILY_CONFIG, family)

        label = "{subset} .{representation} ({asset})".format(
            **context
        )

        node = Node({
            "label": label,
            "version": context["version"],

            # Version data
            "time": version_data.get("time", None),
            "author": version_data.get("author", None),
            "family": family,
            "familyLabel": family_config.get("label", family),
            "familyIcon": family_config.get('icon', None),
        })

        # Collect its dependencies and recursively populate them too
        if self.mode == self.INPUTS:
            for input_ in get_inputs(representation_id):
                self._add_representation(input_, parent=node)
        elif self.mode == self.OUTPUTS:
            for output in get_outputs(representation_id):
                output_id = output["_id"]
                self._add_representation(output_id, parent=node)
        else:
            raise ValueError("Invalid mode: %s" % self.mode)

        self.add_child(node, parent=parent)

    def data(self, index, role):

        if not index.isValid():
            return

        # Show icons
        if role == QtCore.Qt.DecorationRole:
            if index.column() == 0:
                return self._icons["subset"]

            if index.column() == 1:
                return index.internalPointer()['familyIcon']

        return super(RepresentationInputOutputModel, self).data(index, role)


class RepresentationWidget(QtWidgets.QWidget):
    """A Widget showing the inputs/outputs for a Representation."""

    def __init__(self, parent=None):
        super(RepresentationWidget, self).__init__(parent=parent)

        mode_checkboxes = QtWidgets.QGroupBox()
        hbox = QtWidgets.QHBoxLayout(mode_checkboxes)
        hbox.setContentsMargins(0, 0, 0, 0)
        input = QtWidgets.QRadioButton("Inputs")
        input.setChecked(True)
        output = QtWidgets.QRadioButton("Outputs")
        hbox.addWidget(input)
        hbox.addWidget(output)
        hbox.addStretch()

        model = RepresentationInputOutputModel()

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
        layout.addWidget(mode_checkboxes)
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

        self.mode_input = input
        self.mode_output = output

        self.model = model
        self.view = view

        # settings and connections
        self.view.setModel(self.model)

        input.clicked.connect(self.on_mode_changed)
        output.clicked.connect(self.on_mode_changed)

    def on_mode_changed(self):

        if self.mode_input.isChecked():
            # assume it's input
            self.model.set_mode(self.model.INPUTS)
            self.model.refresh()
        else:
            self.model.set_mode(self.model.OUTPUTS)
            self.model.refresh()

        # For now auto expand and auto-resize columns for readability
        self.view.expandAll()
        for i in range(self.model.rowCount(parent=QtCore.QModelIndex())):
            self.view.resizeColumnToContents(i)
