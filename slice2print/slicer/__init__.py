from .config import SlicerConfig
from .slicer import Slicer
from .sliced_model import SlicedModel


class ModelSlicer:
    def __init__(self, cfg, model, update_func):
        self.cfg = cfg
        self.model = model
        self.update_func = update_func

        self.slicer = slicer.Slicer(self.cfg, self.model, update_func)

        self.sliced_model = None

    def execute(self):
        self.slicer.slice()

        if not self.slicer.cancelled:
            self.sliced_model = SlicedModel(self.cfg, self.slicer.contours)
            self.sliced_model.merge_intersecting_meshes()
            self.sliced_model.create_perimeters()

            # intermediate fix to close the progress dialog
            self.update_func(0, "")

    def cancelled(self):
        return self.slicer.cancelled
