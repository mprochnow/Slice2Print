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
import numpy as np
import pyclipper


class LayerPart:
    def __init__(self, cfg, outline):
        self.cfg = cfg
        self.outline = outline
        self.perimeters = []
        self.infill = []
        self.node_count = 0
        self.is_hole = not pyclipper.Orientation(outline)

    def create_perimeters(self):
        self._create_external_perimeters()
        self._create_internal_perimeters()

    def _create_external_perimeters(self):
        solution = self.offset_outline(1, self.cfg.extrusion_width_external_perimeter/2)

        if solution:
            for path in solution:
                self.node_count += len(path)

            self.perimeters.append(solution)

    def _create_internal_perimeters(self):
        if self.perimeters:
            for i in range(1, self.cfg.perimeters):
                solution = self.offset_outline(i+1, self.cfg.extrusion_width/2)

                if len(solution) > 0:
                    for path in solution:
                        self.node_count += len(path)

                    self.perimeters.append(solution)

    def offset_outline(self, nr_of_perimeters, inset):
        """
        Offsets the outline of this layer part by the given number of
        perimeters and than subtract the result with the given inset. This
        ensures that the resulting perimeters will not overlap themselves in
        tight loops.

        :param nr_of_perimeters: How many perimeters should be offset
        :param inset: Value to subtract after offsetting
        :return: List of perimeters, which themselves are lists of x-y-tuples
        """
        is_hole = 1 if self.is_hole else -1

        # TODO Add a small overlap to fill the void area between two perimeters
        offset = self.cfg.extrusion_width_external_perimeter
        offset += (nr_of_perimeters - 1) * self.cfg.extrusion_width

        pco = pyclipper.PyclipperOffset()
        pco.AddPath(self.outline, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

        solution = pco.Execute(offset * is_hole * self.cfg.VERTEX_PRECISION)

        pco.Clear()
        pco.AddPaths(solution, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

        return pco.Execute(-inset * is_hole * self.cfg.VERTEX_PRECISION)


class Layer:
    def __init__(self, cfg, contour, layer_no):
        self.layer_parts = []
        self.perimeters = []
        self.infill = []
        self.cfg = cfg
        self.z = contour.z
        self.layer_no = layer_no

        self._merge_intersecting_meshes(contour)

    def _merge_intersecting_meshes(self, contour):
        pc = pyclipper.Pyclipper()

        for intersections in contour:
            if len(intersections) > 1:
                path = []

                for intersection in intersections:
                    path.append(intersection.xy)

                pc.AddPath(path, pyclipper.PT_SUBJECT, True)

        solution = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

        for outline in solution:
            self.layer_parts.append(LayerPart(self.cfg, outline))

    def create_perimeters(self):
        for layer_part in self.layer_parts:
            layer_part.create_perimeters()

    def create_solid_infill(self):
        pc = pyclipper.Pyclipper()

        # Boundaries for infill
        inset = self.cfg.extrusion_width * self.cfg.infill_overlap / 100.0

        for layer_part in self.layer_parts:
            assert layer_part.perimeters, "Layer part has not perimeters"

            solution = layer_part.offset_outline(self.cfg.perimeters, inset)

            if solution:
                pc.AddPaths(solution, pyclipper.PT_CLIP, True)

        bounds = pc.GetBounds()

        # Create infill lines
        line_length = max(bounds.bottom-bounds.top, bounds.right-bounds.left)

        # TODO Add a small overlap to fill the void area between two perimeters
        extrusion_width = int(self.cfg.extrusion_width_infill * self.cfg.VERTEX_PRECISION)
        infill_inc = int(math.ceil(line_length / extrusion_width))

        if infill_inc > 0:
            infill = list()
            infill.append([[0, -line_length], [0, line_length]])

            for i in range(extrusion_width//2, infill_inc*extrusion_width, extrusion_width):
                x = i + extrusion_width/2
                infill.append([[x, -line_length], [x, line_length]])
                infill.append([[-x, -line_length], [-x, line_length]])

            infill_angle = self.cfg.infill_angle
            if self.layer_no % 2:
                infill_angle += 90

            infill_angle = np.radians(infill_angle)

            c = np.cos(infill_angle)
            s = np.sin(infill_angle)
            rotation_matrix = np.array([[c, -s], [s, c]], np.float32)

            #  Apply infill rotation
            infill = np.matmul(infill, rotation_matrix)

            pc.AddPaths(infill, pyclipper.PT_SUBJECT, False)

            # Clip infill lines
            # (Open paths will be returned as NodeTree, so we have to use PyClipper.Execute2() here)
            solution = pc.Execute2(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)

            if solution.depth > 0:
                assert solution.depth == 1, f"PyClipper.Execute2() returned solution with depth != 1 ({solution.depth})"

                for child in solution.Childs:
                    self.infill.append(child.Contour)

    def __iter__(self):
        yield from self.layer_parts

    @property
    def node_count(self):
        result = 0

        for layer_part in self.layer_parts:
            result += layer_part.node_count

        result += len(self.infill) * 2
        return result


class SlicedModel:
    def __init__(self, cfg, bounding_box, contours):
        self.layers = []
        self.cfg = cfg
        self.bounding_box = bounding_box

        for layer_no, contour in enumerate(contours):
            self.layers.append(Layer(cfg, contour, layer_no))

    def create_perimeters(self):
        for layer in self.layers:
            layer.create_perimeters()

    def create_top_and_bottom_layers(self):
        bottom_layers = self.cfg.bottom_layers
        top_layers = self.cfg.top_layers

        if bottom_layers + top_layers >= len(self.layers):
            bottom_layers = 1
            top_layers = len(self.layers) - 1

        if bottom_layers > 0:
            for layer in self.layers[:bottom_layers]:
                layer.create_solid_infill()

        # if top_layers > 0:
        #     for layer in self.layers[-top_layers:]:
        #         layer.create_solid_infill()

    @property
    def layer_count(self):
        return len(self.layers)

    @property
    def node_count(self):
        result = 0
        for layer in self.layers:
            result += layer.node_count
        return result
