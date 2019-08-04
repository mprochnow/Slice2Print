from .config import SlicerConfig
from .slicer import Slicer, VERTEX_PRECISION


class ModelSlicer:
    def __init__(self, cfg, model, update_func):
        self.cfg = cfg
        self.model = model
        self.update_func = update_func

        update_interval = self.model.facet_count // 100 if self.model.facet_count > 100 else self.model.facet_count
        self.slicer = slicer.Slicer(self.model, self.cfg, update_func, update_interval)

    def execute(self):
        self.slicer.slice()

    def cancelled(self):
        return self.slicer.cancelled

    def get_sliced_model_outlines(self):
        """
        :return: list of pairs of vertices describing a lin [[[x1, y1, z1], [x2, y2, z2]], ...] (for now)
        """
        model = []
        for contour in self.slicer.contours:
            for intersections in contour:
                p1 = p2 = None

                for intersection in intersections:
                    if p1 is None:
                        p1 = intersection
                    elif p2 is None:
                        p2 = intersection
                    else:
                        p1 = p2
                        p2 = intersection

                    if p1 is not None and p2 is not None:
                        model.append([[*p1.intersection], [*p2.intersection]])

                if intersections.closed:
                    model.append([[*intersections.last.intersection],
                                         [*intersections.first.intersection]])

        return model

