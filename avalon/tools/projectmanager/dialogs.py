from ... import io
from ...vendor import qtawesome
from ...vendor.Qt import QtWidgets, QtCore
from ...vendor.jsonschema.exceptions import ValidationError

from . import lib


class TasksCreateDialog(QtWidgets.QDialog):
    """A Dialog to choose a list of Tasks to create."""

    def __init__(self, parent=None):
        super(TasksCreateDialog, self).__init__(parent=parent)
        self.setWindowTitle("Add Tasks")
        self.setModal(True)

        layout = QtWidgets.QVBoxLayout(self)

        label = QtWidgets.QLabel("Select Tasks to create")

        tasks = lib.list_project_tasks()
        tasks = list(sorted(tasks))  # sort for readability
        list_widget = QtWidgets.QListWidget()
        list_widget.addItems(tasks)
        list_widget.setSelectionMode(list_widget.ExtendedSelection)

        footer = QtWidgets.QHBoxLayout()
        cancel = QtWidgets.QPushButton("Cancel")
        create = QtWidgets.QPushButton(qtawesome.icon("fa.plus", color="grey"),
                                       "Create")
        footer.addWidget(create)
        footer.addWidget(cancel)

        layout.addWidget(label)
        layout.addWidget(list_widget)
        layout.addLayout(footer)

        cancel.clicked.connect(self.reject)
        cancel.setAutoDefault(False)

        create.clicked.connect(self.accept)
        create.setAutoDefault(True)

        self.list = list_widget

    def get_selected(self):
        """Return all selected task names

        Returns:
            list: Selected task names.

        """
        return [i.text() for i in self.list.selectedItems()]


class AssetCreateDialog(QtWidgets.QDialog):
    """A Dialog to create a new asset."""

    asset_created = QtCore.Signal(dict)

    def __init__(self, is_silo_required=True, parent=None):
        super(AssetCreateDialog, self).__init__(parent=parent)
        self.setWindowTitle("Add asset")
        self.is_silo_required = is_silo_required

        self.parent_id = None
        self.parent_name = ""

        # Label
        label_label = QtWidgets.QLabel("Label:")
        label = QtWidgets.QLineEdit()
        label.setPlaceholderText("<label>")

        # Silo - backwards compatibility
        silo_label = QtWidgets.QLabel("Silo:")
        silo_label.setVisible(is_silo_required)
        silo_field = QtWidgets.QLineEdit()
        silo_field.setPlaceholderText("<silo>")
        silo_field.setVisible(is_silo_required)

        # Parent
        parent_label = QtWidgets.QLabel("Parent:")
        parent_field = QtWidgets.QLineEdit()
        parent_field.setReadOnly(True)
        parent_field.setStyleSheet("background-color: #333333;")  # greyed out

        # Full name
        name_label = QtWidgets.QLabel("Name:")
        name = QtWidgets.QLineEdit()
        name.setReadOnly(True)
        name.setStyleSheet("background-color: #333333;")  # greyed out

        icon = qtawesome.icon("fa.plus", color="grey")
        add_asset = QtWidgets.QPushButton(icon, "Add")
        add_asset.setAutoDefault(True)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(label_label)
        layout.addWidget(label)
        layout.addWidget(silo_label)
        layout.addWidget(silo_field)
        layout.addWidget(parent_label)
        layout.addWidget(parent_field)
        layout.addWidget(name_label)
        layout.addWidget(name)
        layout.addWidget(add_asset)

        self.data = {
            "labels": {
                "parent": parent_label,
                "silo": silo_label,
                "label": label_label,
                "name": name_label
            },
            "label": {
                "parent": parent_field,
                "silo": silo_field,
                "label": label,
                "name": name
            }
        }

        # Force update the name field
        self.update_name()

        # Signals
        parent_field.textChanged.connect(self.update_name)
        label.textChanged.connect(self.update_name)
        add_asset.clicked.connect(self.on_add_asset)

    def set_silo(self, silo):
        self.data["label"]["silo"].setText(silo or "")

    def set_silo_input_enable(self, enabled=False):
        self.data["label"]["silo"].setEnabled(enabled)

    def set_parent(self, parent_id):

        # Get the parent asset (if any provided)
        parent_name = ""
        if parent_id:
            parent_asset = io.find_one({"_id": parent_id, "type": "asset"})
            assert parent_asset, "Parent asset does not exist."
            parent_name = parent_asset["name"]

            self.parent_name = parent_name
            self.parent_id = parent_id
        else:
            # Clear the parent
            self.parent_name = ""
            self.parent_id = None

        self.data["label"]["parent"].setText(parent_name)

    def update_name(self):
        """Force an update on the long name.

        The long name is based on the asset's label joined with
        the parent's full name.

        """

        label = self.data["label"]["label"].text()
        name = label

        # Prefix with parent name (if parent)
        if self.parent_name:
            name = self.parent_name + "_" + name

        self.data["label"]["name"].setText(name)

    def on_add_asset(self):

        parent_id = self.parent_id
        name = self.data["label"]["name"].text()
        label = self.data["label"]["label"].text()

        if not label:
            QtWidgets.QMessageBox.warning(self, "Missing required label",
                                          "Please fill in asset label.")
            return

        if self.is_silo_required:
            silo_field = self.data["label"]["silo"]
            silo = silo_field.text()
            if not silo:
                QtWidgets.QMessageBox.critical(
                    self, "Missing silo", "Please enter a silo."
                )
                return

        # Name is based on label, so if label passes then name should too
        assert name, "This is a bug"

        data = {
            "name": name,
            "label": label,
            "visualParent": parent_id
        }
        if self.is_silo_required:
            data["silo"] = silo

        # For the launcher automatically add a `group` dataa when the asset
        # is added under a visual parent to look as if it's grouped underneath
        # parent
        if parent_id:
            parent = io.find_one({"_id": io.ObjectId(parent_id)})
            if parent:
                group = parent["name"]
                data["group"] = group

        try:
            lib.create_asset(data, self.is_silo_required)
        except (RuntimeError, AssertionError, ValidationError) as exc:
            QtWidgets.QMessageBox.critical(self, "Add asset failed",
                                           str(exc))
            return

        self.asset_created.emit(data)
