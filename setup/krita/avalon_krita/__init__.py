import os
import sys

from krita import *

class AvalonExtension(Extension):

    def __init__(self, parent):
        #This is initialising the parent, always  important when subclassing.
        super().__init__(parent)

    def setup(self):
    
        # Somehow Krita ignores PYTHONPATH variable and the paths
        # are not added to sys.path and thus the packages will not
        # be importable. So we force it ourselves
        for path in os.environ.get("PYTHONPATH", "").split(os.pathsep):
            if not path.strip():
                continue
            if path in sys.path:
                continue
            sys.path.append(path)
    
        import avalon.api
        import avalon.krita
        avalon.api.install(avalon.krita)

    def createActions(self, window):
        pass

# Add the extension to Krita's list of extensions:
Krita.instance().addExtension(AvalonExtension(Krita.instance()))