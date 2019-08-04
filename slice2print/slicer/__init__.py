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

    def cancelled(self):
        return self.slicer.cancelled

    def get_sliced_model_outlines(self):
        """
        :return: list of pairs of vertices describing a line [[[x1, y1, z1], [x2, y2, z2]], ...] (for now)
        """
        model = []

        if self.sliced_model:
            for layer in self.sliced_model.layers:
                z = layer.z * self.cfg.VERTEX_PRECISION
                for layer_part in layer:
                    p1 = p2 = None

                    for point in layer_part.external_perimeter:
                        if p1 is None:
                            p1 = (point[0], point[1], z)
                        elif p2 is None:
                            p2 = (point[0], point[1], z)
                        else:
                            p1 = p2
                            p2 = (point[0], point[1], z)

                        if p1 is not None and p2 is not None:
                            model.append([p1, p2])

                    model.append([(layer_part.external_perimeter[-1][0], layer_part.external_perimeter[-1][1], z),
                                  (layer_part.external_perimeter[0][0], layer_part.external_perimeter[0][1], z)])

                    if self.cfg.perimeters > 1:
                        for perimeter in layer_part.perimeters:
                            for perimeter_part in perimeter:
                                p1 = p2 = None

                                for point in perimeter_part:
                                    if p1 is None:
                                        p1 = (point[0], point[1], z)
                                    elif p2 is None:
                                        p2 = (point[0], point[1], z)
                                    else:
                                        p1 = p2
                                        p2 = (point[0], point[1], z)

                                    if p1 is not None and p2 is not None:
                                        model.append([p1, p2])

                                model.append([(perimeter_part[-1][0], perimeter_part[-1][1], z),
                                              (perimeter_part[0][0], perimeter_part[0][1], z)])
        return model

