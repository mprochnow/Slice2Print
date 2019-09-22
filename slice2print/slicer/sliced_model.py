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

import math
import pyclipper


class LayerPart:
    def __init__(self, cfg, outline):
        self.cfg = cfg
        self.outline = outline
        self.perimeters = []
        self.infill = []
        self.node_count = 0

    def create_perimeters(self):
        self._create_external_perimeters()
        self._create_internal_perimeters()

    def _create_external_perimeters(self):
        pco = pyclipper.PyclipperOffset()
        pco.AddPath(self.outline, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

        solution = pco.Execute(-self.cfg.extrusion_width_external_perimeter / 2 * self.cfg.VERTEX_PRECISION)

        if len(solution) > 0:
            for path in solution:
                self.node_count += len(path)

            self.perimeters.append(solution)

    def _create_internal_perimeters(self):
        if len(self.perimeters) > 0:
            for i in range(1, self.cfg.perimeters):
                pco = pyclipper.PyclipperOffset()

                for path in self.perimeters[0]:
                    pco.AddPath(path, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

                # TODO Add a small overlap to fill the void area between two perimeters
                offset = i * self.cfg.extrusion_width
                offset -= (self.cfg.extrusion_width-self.cfg.extrusion_width_external_perimeter)/2

                solution = pco.Execute(-offset * self.cfg.VERTEX_PRECISION)

                if len(solution) > 0:
                    for path in solution:
                        self.node_count += len(path)

                    self.perimeters.append(solution)

    def create_solid_infill(self):
        if len(self.perimeters) > 0:
            pc = pyclipper.Pyclipper()

            for perimeter in self.perimeters:
                pc.AddPath(perimeter[-1], pyclipper.PT_CLIP, True)

            bounds = pc.GetBounds()

            extrusion_width = int(self.cfg.extrusion_width * self.cfg.VERTEX_PRECISION)
            infill_inc = int(math.ceil(abs(bounds.top) / extrusion_width))

            infill = []
            for i in range(extrusion_width // 2, infill_inc * extrusion_width, infill_inc):
                infill.append([[bounds.left, i], [bounds.right, i]])
                infill.append([[bounds.left, -i], [bounds.right, -i]])

            # TODO Apply infill rotation

            pc.AddPaths(infill, pyclipper.PT_SUBJECT, False)
            # Open paths will be returned as NodeTree, so we have to use PyClipper.Execute2() here
            solution = pc.Execute2(pyclipper.CT_INTERSECTION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

            if solution.depth > 0:
                assert solution.depth == 1, f"PyClipper.Execute2() return solution with depth != 1 ({solution.depth})"

                for child in solution.Childs:
                    self.infill.append(child.Contour)
                    # TODO Increment node count


class Layer:
    def __init__(self, cfg, contour):
        self.layer_parts = []
        self.perimeters = []
        self.cfg = cfg
        self.z = contour.z
        self.node_count = 0

        # merge intersecting meshes
        pc = pyclipper.Pyclipper()

        for intersections in contour:
            if len(intersections) > 1:
                path = []

                for intersection in intersections:
                    path.append(intersection.xy)

                pc.AddPath(path, pyclipper.PT_SUBJECT, True)

        solution = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

        for outline in solution:
            self.layer_parts.append(LayerPart(cfg, outline))

    def create_perimeters(self):
        for layer_part in self.layer_parts:
            layer_part.create_perimeters()
            self.node_count += layer_part.node_count

    def create_solid_infill(self):
        for layer_part in self.layer_parts:
            layer_part.create_solid_infill()

    def __iter__(self):
        yield from self.layer_parts


class SlicedModel:
    def __init__(self, cfg, bounding_box, contours):
        self.layers = []
        self.cfg = cfg
        self.bounding_box = bounding_box
        self.node_count = 0

        for contour in contours:
            self.layers.append(Layer(cfg, contour))

    def create_perimeters(self):
        for layer in self.layers:
            layer.create_perimeters()
            self.node_count += layer.node_count

    def create_top_and_bottom_layers(self):
        bottom_layers = self.cfg.bottom_layers
        top_layers = self.cfg.top_layers

        if bottom_layers + top_layers >= len(self.layers):
            bottom_layers = 1
            top_layers = len(self.layers) - 1

        for layer in self.layers[:bottom_layers]:
            layer.create_solid_infill()

        for layer in self.layers[-top_layers:]:
            layer.create_solid_infill()

    @property
    def layer_count(self):
        return len(self.layers)
