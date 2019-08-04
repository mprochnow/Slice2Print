# This file is part of Slice2Print.
#
# Slice2Print is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Slice2Print is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Slice2Print.  If not, see <http://www.gnu.org/licenses/>.

import pyclipper


class LayerPart:
    def __init__(self, cfg, external_perimeter):
        self.external_perimeter = external_perimeter
        self.perimeters = []

        # TODO Add a small overlap to fill the void area between two perimeters
        for i in range(1, cfg.perimeters):
            pco = pyclipper.PyclipperOffset()
            pco.AddPath(external_perimeter, pyclipper.JT_SQUARE, pyclipper.ET_CLOSEDPOLYGON)
            solution = pco.Execute(-i*cfg.extrusion_width*cfg.VERTEX_PRECISION)
            self.perimeters.append(solution)


class Layer:
    def __init__(self, z):
        self.layer_parts = []
        self.z = z

    def add_layer_part(self, island):
        self.layer_parts.append(island)

    def __iter__(self):
        yield from self.layer_parts


class SlicedModel:
    def __init__(self, cfg, contours):
        self.layers = []

        for contour in contours:
            layer = Layer(contour.z)

            for intersections in contour:
                path = []

                for intersection in intersections:
                    path.append((intersection.vertex.x, intersection.vertex.y))

                pco = pyclipper.PyclipperOffset()
                pco.AddPath(path, pyclipper.JT_SQUARE, pyclipper.ET_CLOSEDPOLYGON)

                for i in range(cfg.perimeters):
                    solution = pco.Execute(-cfg.extrusion_width_external_perimeter/2*cfg.VERTEX_PRECISION)

                    for p in solution:
                        layer.add_layer_part(LayerPart(cfg, p))

            self.layers.append(layer)
