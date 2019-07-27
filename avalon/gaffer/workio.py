"""Host API required Work Files tool"""
import os
import Gaffer


def file_extensions():
    return [".gfr"]


def has_unsaved_changes():
    # todo: implement
    raise NotImplementedError("Not implemented..")


def save(filepath):
    # todo: implement
    raise NotImplementedError("Not implemented..")


def open(filepath):
    # todo: implement
    raise NotImplementedError("Not implemented..")


def current_file():
    # todo: implement
    raise NotImplementedError("Not implemented..")


def work_root():
    from avalon import api

    work_dir = api.Session["AVALON_WORKDIR"]
    scene_dir = api.Session.get("AVALON_SCENEDIR")
    if scene_dir:
        return os.path.join(work_dir, scene_dir)
    else:
        return work_dir
