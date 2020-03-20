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


class EmptyLayerException(Exception):
    pass


class Layer:
    MIN_DIST_BETWEEN_POINTS = 50

    def __init__(self, cfg, contour, layer_no):
        self.outlines = []
        self.perimeters = []
        self.infill = []
        self.cfg = cfg
        self.z = contour.z
        self.layer_no = layer_no
        self.layer_height = (cfg.layer_height if layer_no > 0 else cfg.first_layer_height)
        self.node_count = 0

        self._merge_intersecting_meshes(contour)

    def _merge_intersecting_meshes(self, contour):
        def dist_longer_than(p1, p2, d):
            x = p2[0] - p1[0]
            y = p2[1] - p1[1]
            return d*d < x**2 + y**2

        pc = pyclipper.Pyclipper()

        for intersections in contour:
            if len(intersections) > 1:
                path = []

                for intersection in intersections:
                    if not path or path and dist_longer_than(path[-1], intersection.xy, self.MIN_DIST_BETWEEN_POINTS):
                        path.append(intersection.xy)

                if len(path) > 2:
                    pc.AddPath(path, pyclipper.PT_SUBJECT, True)

        try:
            solution = pc.Execute(pyclipper.CT_UNION, pyclipper.PFT_NONZERO, pyclipper.PFT_NONZERO)

            for outline in solution:
                self.outlines.append(outline)
        except pyclipper.ClipperException:
            # Nothing to clip, i.e. no paths were added to the Pyclipper instance
            raise EmptyLayerException

    def create_perimeters(self):
        self._create_external_perimeters()
        self._create_internal_perimeters()

    def _create_external_perimeters(self):
        inset = self.cfg.extrusion_width_external_perimeter / 2

        solution = offset_outlines(self.cfg, self.layer_height, self.outlines, 1, inset)

        if solution:
            for path in solution:
                self.node_count += len(path)

            self.perimeters.append(solution)
        else:
            raise EmptyLayerException

    def _create_internal_perimeters(self):
        inset = self.cfg.extrusion_width / 2

        for i in range(1, self.cfg.perimeters):
            solution = offset_outlines(self.cfg, self.layer_height, self.outlines, i+1, inset)

            if solution:
                for path in solution:
                    self.node_count += len(path)

                self.perimeters.append(solution)
            else:
                break  # Nothing more to do here

    def create_infill(self):
        pc = pyclipper.Pyclipper()

        # Boundaries for infill
        inset = self.cfg.extrusion_width * self.cfg.infill_overlap / 100.0
        solution = offset_outlines(self.cfg, self.layer_height, self.outlines, self.cfg.perimeters, inset)

        if solution:
            pc.AddPaths(solution, pyclipper.PT_CLIP, True)

            # Create infill lines
            bounds = pc.GetBounds()
            line_length = max(bounds.bottom-bounds.top, bounds.right-bounds.left)

            line_distance = int(
                (self.cfg.extrusion_width_infill - self.cfg.extrusion_overlap_factor/2) * self.cfg.VERTEX_PRECISION)
            infill_inc = int(math.ceil(line_length / line_distance))

            if infill_inc > 0:
                infill = list()
                infill.append([[0, -line_length], [0, line_length]])

                for i in range(line_distance//2, infill_inc*line_distance, line_distance):
                    x = i + line_distance/2
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
                        self.node_count += 2

            # self.node_count += len(self.infill) * 2

    def to_svg(self, filename):
        with open(filename, "w") as f:
            f.write('<?xml version="1.0" standalone="no"?>\n')
            f.write('<svg xmlns="http://www.w3.org/2000/svg" version="1.1" viewBox="-100 -100 200 200">\n')
            f.write('<path d="')

            for outline in self.outlines:
                first = None
                for x, y in outline:
                    if first is None:
                        f.write(f'M {x/self.cfg.VERTEX_PRECISION} {-y/self.cfg.VERTEX_PRECISION}')
                        first = (x, y)
                    else:
                        f.write(f' L {x/self.cfg.VERTEX_PRECISION} {-y/self.cfg.VERTEX_PRECISION}')

                f.write(f' L {first[0]/self.cfg.VERTEX_PRECISION} {-first[1]/self.cfg.VERTEX_PRECISION}')

            f.write('" fill="none" stroke="black" stroke-width="0.1"/>')
            f.write('</svg>\n')


class SlicedModel:
    def __init__(self, cfg, bounding_box, contours):
        self.layers = []
        self.cfg = cfg
        self.bounding_box = bounding_box

        for layer_no, contour in enumerate(contours):
            try:
                self.layers.append(Layer(cfg, contour, layer_no))
            except EmptyLayerException:
                pass

    def create_perimeters(self):
        try:
            for layer in self.layers:
                layer.create_perimeters()
        except EmptyLayerException:
            self.layers.remove(layer)

    def create_infill(self):
        bottom_layers = self.cfg.bottom_layers
        top_layers = self.cfg.top_layers

        if bottom_layers + top_layers >= len(self.layers):
            bottom_layers = 1
            top_layers = len(self.layers) - 1

        if bottom_layers > 0:
            for layer in self.layers[:bottom_layers]:
                layer.create_infill()

        if top_layers > 0:
            for layer in self.layers[-top_layers:]:
                layer.create_infill()

        self.create_island_top_layers(bottom_layers, top_layers)

    # TODO needs work
    def create_island_top_layers(self, bottom_layers, top_layers):
        pc = pyclipper.Pyclipper()

        # Loop backwards through the layers
        for i in range(len(self.layers)-1, 1, -1):
            lower_layer = self.layers[i - 1]
            current_layer = self.layers[i]

            # Subtract current layer from lower layer
            pc.AddPaths(current_layer.outlines, pyclipper.PT_CLIP, True)
            pc.AddPaths(lower_layer.outlines, pyclipper.PT_SUBJECT, True)

            solution = pc.Execute(pyclipper.CT_DIFFERENCE, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
            if solution:
                pc.Clear()

                pc.AddPaths(solution, pyclipper.PT_CLIP, True)

                bounds = pc.GetBounds()
                line_length = max(bounds.bottom-bounds.top, bounds.right-bounds.left)
                x0 = bounds.right - bounds.left
                y0 = bounds.bottom - bounds.top

                line_distance = int((self.cfg.extrusion_width_infill - self.cfg.extrusion_overlap_factor/2) *
                                    self.cfg.VERTEX_PRECISION)
                infill_inc = int(math.ceil(line_length / line_distance))
                if infill_inc > 0:
                    infill = list()
                    infill.append([[0, -line_length], [0, line_length]])

                    for j in range(line_distance//2, infill_inc*line_distance, line_distance):
                        x = j + line_distance/2
                        infill.append([[x, -line_length], [x, line_length]])
                        infill.append([[-x, -line_length], [-x, line_length]])

                    infill_angle = self.cfg.infill_angle
                    if lower_layer.layer_no % 2:
                        infill_angle += 90

                    infill_angle = np.radians(infill_angle)

                    c = np.cos(infill_angle)
                    s = np.sin(infill_angle)
                    rotation_matrix = np.array([[c, -s], [s, c]], np.float32)

                    translation_matrix = np.identity(2, np.float32)
                    translation_matrix[1][0] = x0
                    translation_matrix[1][1] = y0

                    #  Apply infill rotation
                    infill = np.matmul(infill, rotation_matrix)

                    infill = np.matmul(infill, translation_matrix)

                    pc.AddPaths(infill, pyclipper.PT_SUBJECT, False)

                    # Clip infill lines
                    # (Open paths will be returned as NodeTree, so we have to use PyClipper.Execute2() here)
                    solution = pc.Execute2(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)

                    if solution.depth > 0:
                        assert solution.depth == 1, \
                            f"PyClipper.Execute2() returned solution with depth != 1 ({solution.depth})"

                        for child in solution.Childs:
                            lower_layer.infill.append(child.Contour)
                            lower_layer.node_count += 2

            pc.Clear()

    @property
    def layer_count(self):
        return len(self.layers)

    @property
    def node_count(self):
        result = 0
        for layer in self.layers:
            result += layer.node_count
        return result


def offset_outlines(cfg, layer_height, outlines, nr_of_perimeters, inset):
    """
    Offsets the outline of this layer by the given number of perimeters
    and than subtract the result with the given inset. This ensures that
    the resulting perimeters will not overlap themselves in tight loops.

    :param cfg: Instance of SlicerConfig
    :param layer_height: Layer height
    :param outlines: List of closed paths which should be offset
    :param nr_of_perimeters: How many perimeters should be offset
    :param inset: Value to subtract after offsetting
    :return: Result of PyclipperOffset.Execute()
    """
    pco = pyclipper.PyclipperOffset()

    offset = cfg.extrusion_width_external_perimeter
    offset += (nr_of_perimeters - 1) * cfg.extrusion_width
    offset -= (nr_of_perimeters - 1) * layer_height * cfg.extrusion_overlap_factor

    pco.AddPaths(outlines, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

    solution = pco.Execute(-offset * cfg.VERTEX_PRECISION)

    pco.Clear()
    pco.AddPaths(solution, pyclipper.JT_MITER, pyclipper.ET_CLOSEDPOLYGON)

    return pco.Execute(inset * cfg.VERTEX_PRECISION)
