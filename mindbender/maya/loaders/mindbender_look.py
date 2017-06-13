import os
import json

from maya import cmds
from mindbender import api


class LookLoader(api.Loader):
    """Specific loader for lookdev"""

    families = ["mindbender.lookdev"]
    representations = ["ma"]

    def process(self, name, namespace, context):
        from mindbender import maya
        try:
            existing_reference = cmds.file(self.fname,
                                           query=True,
                                           referenceNode=True)
        except RuntimeError as e:
            if e.message.rstrip() != "Cannot find the scene file.":
                raise

            self.log.info("Loading lookdev for the first time..")
            with maya.maintained_selection():
                nodes = cmds.file(
                    self.fname,
                    namespace=namespace,
                    reference=True,
                    returnNewNodes=True
                )
        else:
            self.log.info("Reusing existing lookdev..")
            nodes = cmds.referenceQuery(existing_reference, nodes=True)
            namespace = nodes[0].split(":", 1)[0]

        # Assign shaders
        self.fname = self.fname.rsplit(".", 1)[0] + ".json"

        if not os.path.isfile(self.fname):
            self.log.warning("Look development asset "
                             "has no relationship data.")
            return nodes

        with open(self.fname) as f:
            relationships = json.load(f)

        maya.apply_shaders(relationships, namespace)

        self[:] = nodes
