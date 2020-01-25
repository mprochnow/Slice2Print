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


class Layer:
    def __init__(self, cfg, contour, layer_no):
        self.outlines = []
        self.perimeters = []
        self.infill = []
        self.cfg = cfg
        self.z = contour.z
        self.layer_no = layer_no
        self.node_count = 0

        self._merge_intersecting_meshes(contour)

    def _merge_intersecting_meshes(self, contour):
        pc = pyclipper.Pyclipper()

        for intersections in contour:
            if len(intersections) > 1:
                path = []

                for intersection in intersections:
                    # Ensure that each element in path is different
                    if not path or path and path[-1] != intersection.xy:
                        path.append(intersection.xy)

                if len(path) > 1:
                    pc.AddPath(path, pyclipper.PT_SUBJECT, True)

        solution = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

        for outline in solution:
            self.outlines.append(outline)

    def create_perimeters(self):
        self._create_external_perimeters()
        self._create_internal_perimeters()

    def _create_external_perimeters(self):
        inset = self.cfg.extrusion_width_external_perimeter / 2

        solution = self._offset_outline(1, inset)

        if solution:
            for path in solution:
                self.node_count += len(path)

            self.perimeters.append(solution)

    def _create_internal_perimeters(self):
        inset = self.cfg.extrusion_width / 2

        for i in range(1, self.cfg.perimeters):
            solution = self._offset_outline(i+1, inset)

            if solution:
                for path in solution:
                    self.node_count += len(path)

                self.perimeters.append(solution)
            else:
                break  # Nothing more to do here

    def create_solid_infill(self):
        pc = pyclipper.Pyclipper()

        # Boundaries for infill
        inset = self.cfg.extrusion_width * self.cfg.infill_overlap / 100.0

        solution = self._offset_outline(self.cfg.perimeters, inset)
        assert solution, "No boundaries for infill"
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

        self.node_count += len(self.infill) * 2

    def _offset_outline(self, nr_of_perimeters, inset):
        """
        Offsets the outline of this layer by the given number of perimeters
        and than subtract the result with the given inset. This ensures that
        the resulting perimeters will not overlap themselves in tight loops.

        :param nr_of_perimeters: How many perimeters should be offset
        :param inset: Value to subtract after offsetting
        :return: Result of PyclipperOffset.Execute()
        """
        pco = pyclipper.PyclipperOffset()

        offset = self.cfg.extrusion_width_external_perimeter
        offset += (nr_of_perimeters -1) * self.cfg.extrusion_width

        for outline in self.outlines:
            pco.AddPath(outline, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

        solution = pco.Execute(-offset * self.cfg.VERTEX_PRECISION)

        pco.Clear()
        pco.AddPaths(solution, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

        return pco.Execute(inset * self.cfg.VERTEX_PRECISION)


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
