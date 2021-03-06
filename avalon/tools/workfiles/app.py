import sys
import os
import getpass
import re
import shutil


from ...vendor.Qt import QtWidgets, QtCore
from ... import style
from ... import io, api


def determine_application():
        # Determine executable
        application = None

        basename = os.path.basename(sys.executable).lower()

        if "maya" in basename:
            application = "maya"

        if application is None:
            raise ValueError(
                "Could not determine application from executable:"
                " \"{0}\"".format(sys.executable)
            )

        return application


class NameWindow(QtWidgets.QDialog):
    """Name Window"""

    def __init__(self, root):
        super(NameWindow, self).__init__()
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint)

        self.result = None
        self.setup(root)

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        grid_layout = QtWidgets.QGridLayout()

        label = QtWidgets.QLabel("Version:")
        grid_layout.addWidget(label, 0, 0)
        self.version_spinbox = QtWidgets.QSpinBox()
        self.version_spinbox.setMinimum(1)
        self.version_spinbox.setMaximum(9999)
        self.version_checkbox = QtWidgets.QCheckBox("Next Available Version")
        self.version_checkbox.setCheckState(QtCore.Qt.CheckState(2))
        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.version_spinbox)
        layout.addWidget(self.version_checkbox)
        grid_layout.addLayout(layout, 0, 1)
        # Since the version can be padded with "{version:0>4}" we only search
        # for "{version".
        if "{version" not in self.template:
            label.setVisible(False)
            self.version_spinbox.setVisible(False)
            self.version_checkbox.setVisible(False)

        label = QtWidgets.QLabel("Comment:")
        grid_layout.addWidget(label, 1, 0)
        self.comment_lineedit = QtWidgets.QLineEdit()
        if "{comment}" not in self.template:
            label.setVisible(False)
            self.comment_lineedit.setVisible(False)
        grid_layout.addWidget(self.comment_lineedit, 1, 1)

        grid_layout.addWidget(QtWidgets.QLabel("Preview:"), 2, 0)
        self.label = QtWidgets.QLabel("File name")
        grid_layout.addWidget(self.label, 2, 1)

        self.layout.addLayout(grid_layout)

        layout = QtWidgets.QHBoxLayout()
        self.ok_button = QtWidgets.QPushButton("Ok")
        layout.addWidget(self.ok_button)
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        layout.addWidget(self.cancel_button)
        self.layout.addLayout(layout)

        self.version_spinbox.valueChanged.connect(
            self.on_version_spinbox_changed
        )
        self.version_checkbox.stateChanged.connect(
            self.on_version_checkbox_changed
        )
        self.comment_lineedit.textChanged.connect(self.on_comment_changed)
        self.ok_button.pressed.connect(self.on_ok_pressed)
        self.cancel_button.pressed.connect(self.on_cancel_pressed)

        self.refresh()

    def on_version_spinbox_changed(self, value):
        self.data["version"] = value
        self.refresh()

    def on_version_checkbox_changed(self, value):
        self.refresh()

    def on_comment_changed(self, text):
        self.data["comment"] = text
        self.refresh()

    def on_ok_pressed(self):
        self.result = self.work_file.replace("\\", "/")
        self.close()

    def on_cancel_pressed(self):
        self.close()

    def get_result(self):
        return self.result

    def get_work_file(self, template=None):
        data = self.data.copy()
        template = template or self.template

        if not data["comment"]:
            data.pop("comment", None)

        # Remove optional missing keys
        pattern = re.compile(r"<.*?>")
        invalid_optionals = []
        for group in pattern.findall(template):
            try:
                group.format(**data)
            except KeyError:
                invalid_optionals.append(group)

        for group in invalid_optionals:
            template = template.replace(group, "")

        work_file = template.format(**data)

        # Remove optional symbols
        work_file = work_file.replace("<", "")
        work_file = work_file.replace(">", "")

        work_file = work_file + self.extensions[self.application]

        return work_file

    def refresh(self):
        if self.version_checkbox.isChecked():
            self.version_spinbox.setEnabled(False)

            # Find matching files
            files = os.listdir(self.root)

            # Fast match on extension
            ext = self.extensions[self.application]
            files = [f for f in files if f.endswith(ext)]

            # Build template without optionals, version to digits only regex
            # and comment to any definable value.
            # Note: with auto-increment the `version` key may not be optional.
            template = self.template
            template = re.sub("<.*?>", ".*?", template)
            template = re.sub("{version.*}", "([0-9]+)", template)
            template = re.sub("{comment.*?}", ".+?", template)
            template = self.get_work_file(template)
            template = "^" + template + "$"           # match beginning to end

            # Get highest version among existing matching files
            version = 1
            for file in sorted(files):
                match = re.match(template, file)
                if not match:
                    continue

                file_version = int(match.group(1))

                if file_version >= version:
                    version = file_version + 1

            self.data["version"] = version

            # safety check
            path = os.path.join(self.root, self.get_work_file())
            assert not os.path.exists(path), \
                "This is a bug, file exists: %s" % path

        else:
            self.version_spinbox.setEnabled(True)
            self.data["version"] = self.version_spinbox.value()

        self.work_file = self.get_work_file()

        self.label.setText(
            "<font color='green'>{0}</font>".format(self.work_file)
        )
        if os.path.exists(os.path.join(self.root, self.work_file)):
            self.label.setText(
                "<font color='red'>Cannot create \"{0}\" because file exists!"
                "</font>".format(self.work_file)
            )
            self.ok_button.setEnabled(False)
        else:
            self.ok_button.setEnabled(True)

    def setup(self, root):
        self.root = root
        self.application = determine_application()

        # Get work file name
        self.data = {
            "project": io.find_one(
                {"name": api.Session["AVALON_PROJECT"], "type": "project"}
            ),
            "asset": io.find_one(
                {"name": api.Session["AVALON_ASSET"], "type": "asset"}
            ),
            "task": {
                "name": api.Session["AVALON_TASK"].lower(),
                "label": api.Session["AVALON_TASK"]
            },
            "version": 1,
            "user": getpass.getuser(),
            "comment": ""
        }

        self.template = "{task[name]}_v{version:0>4}<_{comment}>"
        templates = self.data["project"]["config"]["template"]
        if "workfile" in templates:
            self.template = templates["workfile"]

        self.extensions = {"maya": ".ma"}


class Window(QtWidgets.QDialog):
    """Work Files Window"""

    def __init__(self, root=None):
        super(Window, self).__init__()
        self.setWindowTitle("Work Files")
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)

        self.root = root
        if self.root is None:
            self.root = os.getcwd()

        filters = {
            "maya": [".ma", ".mb"]
        }
        self.application = determine_application()
        self.filter = filters[self.application]

        self.layout = QtWidgets.QVBoxLayout()
        self.setLayout(self.layout)

        # Display current context
        # todo: context should update on update task
        label = u"<b>Asset</b> {0} \u25B6 <b>Task</b> {1}".format(
            api.Session["AVALON_ASSET"],
            api.Session["AVALON_TASK"]
        )
        self.context_label = QtWidgets.QLabel(label)
        self.context_label.setStyleSheet("QLabel{ font-size: 12pt; }")
        self.layout.addWidget(self.context_label)

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Plain)
        self.layout.addWidget(separator)

        self.list = QtWidgets.QListWidget()
        self.layout.addWidget(self.list)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.duplicate_button = QtWidgets.QPushButton("Duplicate")
        buttons_layout.addWidget(self.duplicate_button)
        self.open_button = QtWidgets.QPushButton("Open")
        buttons_layout.addWidget(self.open_button)
        self.browse_button = QtWidgets.QPushButton("Browse")
        buttons_layout.addWidget(self.browse_button)
        self.layout.addLayout(buttons_layout)

        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.layout.addWidget(separator)

        current_file_label = QtWidgets.QLabel(
            "Current File: " + self.current_file()
        )
        self.layout.addWidget(current_file_label)

        buttons_layout = QtWidgets.QHBoxLayout()
        self.save_as_button = QtWidgets.QPushButton("Save As")
        buttons_layout.addWidget(self.save_as_button)
        self.layout.addLayout(buttons_layout)

        self.duplicate_button.pressed.connect(self.on_duplicate_pressed)
        self.open_button.pressed.connect(self.on_open_pressed)
        self.list.doubleClicked.connect(self.on_open_pressed)
        self.browse_button.pressed.connect(self.on_browse_pressed)
        self.save_as_button.pressed.connect(self.on_save_as_pressed)

        self.open_button.setFocus()

        self.refresh()
        self.resize(400, 550)

    def get_name(self):

        window = NameWindow(self.root)
        window.setStyleSheet(style.load_stylesheet())
        window.exec_()

        return window.get_result()

    def current_file(self):
        func = {"maya": self.current_file_maya}
        return func[self.application]()

    def current_file_maya(self):
        import os
        from maya import cmds

        current_file = cmds.file(sceneName=True, query=True)

        # Maya returns forward-slashes by default
        normalised = os.path.basename(os.path.normpath(current_file))

        # Unsaved current file
        if normalised == ".":
            return "NOT SAVED"

        return normalised

    def refresh(self):
        self.list.clear()

        modified = []
        for f in sorted(os.listdir(self.root)):
            path = os.path.join(self.root, f)
            if os.path.isdir(path):
                continue

            if self.filter and os.path.splitext(f)[1] not in self.filter:
                continue

            self.list.addItem(f)
            modified.append(os.path.getmtime(path))

        # Select last modified file
        if self.list.count():
            item = self.list.item(modified.index(max(modified)))
            item.setSelected(True)

            # Scroll list so item is visible
            QtCore.QTimer.singleShot(100, lambda: self.list.scrollToItem(item))

            self.duplicate_button.setEnabled(True)
        else:
            self.duplicate_button.setEnabled(False)

        self.list.setMinimumWidth(self.list.sizeHintForColumn(0) + 30)

    def save_as_maya(self, file_path):
        from maya import cmds
        cmds.file(rename=file_path)
        cmds.file(save=True, type="mayaAscii")

    def save_changes_prompt(self):
        messagebox = QtWidgets.QMessageBox()
        messagebox.setWindowFlags(QtCore.Qt.FramelessWindowHint)
        messagebox.setIcon(messagebox.Warning)
        messagebox.setWindowTitle("Unsaved Changes!")
        messagebox.setText(
            "There are unsaved changes to the current file."
            "\nDo you want to save the changes?"
        )
        messagebox.setStandardButtons(
            messagebox.Yes | messagebox.No | messagebox.Cancel
        )
        result = messagebox.exec_()

        if result == messagebox.Yes:
            return True
        elif result == messagebox.No:
            return False
        else:
            return None

    def open_maya(self, file_path):
        from maya import cmds

        force = False
        if cmds.file(q=True, modified=True):
            result = self.save_changes_prompt()

            if result is None:
                return False

            if result:
                cmds.file(save=True, type="mayaAscii")
            else:
                force = True

        cmds.file(file_path, open=True, force=force)

        return True

    def open(self, file_path):
        func = {"maya": self.open_maya}

        work_file = os.path.join(
            self.root, self.list.selectedItems()[0].text()
        )

        return func[self.application](work_file)

    def on_duplicate_pressed(self):
        work_file = self.get_name()

        if not work_file:
            return

        src = os.path.join(
            self.root, self.list.selectedItems()[0].text()
        )
        dst = os.path.join(
            self.root, work_file
        )
        shutil.copy(src, dst)

        self.refresh()

    def on_open_pressed(self):
        work_file = os.path.join(
            self.root, self.list.selectedItems()[0].text()
        )

        result = self.open(work_file)

        if result:
            self.close()

    def on_browse_pressed(self):

        filter = " *".join(self.filter)
        filter = "Work File (*{0})".format(filter)
        work_file = QtWidgets.QFileDialog.getOpenFileName(
            caption="Work Files",
            dir=self.root,
            filter=filter
        )[0]

        if not work_file:
            self.refresh()
            return

        self.open(work_file)

        self.close()

    def on_save_as_pressed(self):
        work_file = self.get_name()

        if not work_file:
            return

        save_as = {"maya": self.save_as_maya}
        application = determine_application()
        if application not in save_as:
            raise ValueError(
                "Could not find a save as method for this application."
            )

        file_path = os.path.join(self.root, work_file)

        save_as[application](file_path)

        self.close()


def show(root):
    """Show Work Files GUI"""
    window = Window(root)
    window.setStyleSheet(style.load_stylesheet())
    window.exec_()
