import logging
import ix

from .. import api, io


log = logging.getLogger(__name__)


def reset_frame_range():
    """ Set timeine frame range.
    """
    
    fps = float(api.Session.get("AVALON_FPS", 25))
    ix.cmds.SetFps(fps)

    name = api.Session["AVALON_ASSET"]
    asset = io.find_one({"name": name, "type": "asset"})
    asset_data = asset["data"]
    frame_start = str(asset_data.get(
        "frameStart",
        asset_data.get("edit_in")))

    frame_end = str(asset_data.get(
        "frameEnd",
        asset_data.get("edit_out")))
    log.info(frame_start)
    log.info(frame_end)

    ix.begin_command_batch("Avalon: reset frame range")
    image = "project://scene/image"
    ix.cmds.SetValue(image + ".background.first_frame", frame_start)
    ix.cmds.SetValue(image + ".background.last_frame", frame_end)
    ix.cmds.SetCurrentFrameRange(float(frame_start), float(frame_end))
    log.info("Frame range set")
    ix.end_command_batch()


def reset_resolution():
    """Set resolution to project resolution."""
    project = io.find_one({"type": "project"})
    project_data = project["data"]

    width = project_data.get("resolution_width",
                             project_data.get("resolutionWidth"))
    height = project_data.get("resolution_height",
                              project_data.get("resolutionHeight"))

    if not width or not height:
        log.info("No width or height set in project. "
                 "Skipping reset resolution..")
        return

    image = ix.get_item('project://scene/image')
    current_width = image.attrs.resolution[0]
    current_height = image.attrs.resolution[1]

    ix.begin_command_batch("Avalon: reset resolution")
    if width != current_width or height != current_height:
        image.attrs.resolution_preset = "Custom"
        image.attrs.resolution[0] = width
        image.attrs.resolution[1] = height
        image.attrs.resolution_multiplier = "2"
    ix.end_command_batch()
