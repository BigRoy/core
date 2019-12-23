"""Host API required Work Files tool"""
import krita


def _active_document():
    """Helper function to return current active document"""
    return krita.Krita.instance().activeDocument()


def file_extensions():
    return [".kra",
            # Krita can also open Photoshop documents
            ".psd"]


def has_unsaved_changes():
    document = _active_document()
    if document:
        return document.modified()
    else:
        return False


def save_file(filepath):
    document = _active_document()
    if document:
        return document.saveAs(filepath)
    else:
        return False


def open_file(filepath):

    app = krita.Krita.instance()
    document = app.openDocument(filepath)

    # By default Krita doesn't open a view to show the new document
    # and it is only accessible through Window > New View. For usability
    # we will force a new view as a user would expect.
    app.activeWindow().addView(document)

    # Make it the active document
    app.setActiveDocument(document)


def current_file():
    document = _active_document()
    if document:
        return document.fileName()


def work_root():
    from avalon import Session

    work_dir = Session["AVALON_WORKDIR"]
    scene_dir = Session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
