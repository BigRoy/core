import importlib

import avalon.api
import avalon.fusion

assert tool, "Tool must be given as input to RunScript"

print("Installing Fusion host..")
avalon.api.install(avalon.fusion)

print("Running tool: %s" % tool)
module = importlib.import_module("avalon.tools.{0}".format(tool))
module.show()