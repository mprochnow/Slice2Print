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


class Layer:
    def __init__(self, cfg, z):
        self.layer_parts = []
        self.perimeters = []
        self.cfg = cfg
        self.z = z

    def add_layer_part(self, layer_part):
        self.layer_parts.append(layer_part)

    def merge_intersecting_layer_parts(self):
        pc = pyclipper.Pyclipper()

        for layer_part in self.layer_parts:
            if len(layer_part) > 1:
                pc.AddPath(layer_part, pyclipper.PT_SUBJECT, True)

        solution = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

        self.layer_parts = solution

    def create_perimeters(self):
        self._create_external_perimeters()
        self._create_internal_perimeters()

    def _create_external_perimeters(self):
        pco = pyclipper.PyclipperOffset()

        for layer_part in self.layer_parts:
            pco.AddPath(layer_part, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

        solution = pco.Execute(-self.cfg.extrusion_width_external_perimeter / 2 * self.cfg.VERTEX_PRECISION)

        self.perimeters.append(solution)

    def _create_internal_perimeters(self):
        for i in range(1, self.cfg.perimeters):
            pco = pyclipper.PyclipperOffset()

            for layer_part in self.perimeters[0]:
                # TODO Add a small overlap to fill the void area between two perimeters
                pco.AddPath(layer_part, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

            solution = pco.Execute(-i * self.cfg.extrusion_width * self.cfg.VERTEX_PRECISION)

            self.perimeters.append(solution)

    def __iter__(self):
        yield from self.layer_parts


class SlicedModel:
    def __init__(self, cfg, contours):
        self.layers = []

        for contour in contours:
            layer = Layer(cfg, contour.z)

            for intersections in contour:
                layer_part = []

                for intersection in intersections:
                    layer_part.append((intersection.vertex.x, intersection.vertex.y))

                layer.add_layer_part(layer_part)

            self.layers.append(layer)

    def merge_intersecting_meshes(self):
        for layer in self.layers:
            layer.merge_intersecting_layer_parts()

    def create_perimeters(self):
        for layer in self.layers:
            layer.create_perimeters()

    @property
    def layer_count(self):
        return len(self.layers)
