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


def line_infill(cfg, layer_no, outlines):
    """

    :param cfg: Instance of SlicerConfig
    :param layer_no: Layer number
    :param outlines: List of closed path which should be infilled
    :return: List of lines
    """
    result = list()
    pc = pyclipper.Pyclipper()

    pc.AddPaths(outlines, pyclipper.PT_CLIP, True)

    bounds = pc.GetBounds()
    x0 = bounds.left + (bounds.right - bounds.left) / 2
    y0 = bounds.top + (bounds.bottom - bounds.top) / 2

    line_length = max(bounds.bottom-bounds.top, bounds.right-bounds.left)
    line_distance = int((cfg.extrusion_width_infill - cfg.extrusion_overlap_factor/2) * cfg.VERTEX_PRECISION)
    infill_inc = int(math.ceil(line_length / line_distance))

    if infill_inc > 0:
        infill = list()

        infill.append([[0, -line_length, 1], [0, line_length, 1]])

        for j in range(line_distance//2, infill_inc*line_distance, line_distance):
            x = j + line_distance / 2
            infill.append([[x, -line_length, 1], [x, line_length, 1]])
            infill.append([[-x, -line_length, 1], [-x, line_length, 1]])

        infill_angle = cfg.infill_angle
        if layer_no % 2:
            infill_angle += 90

        infill_angle = np.radians(infill_angle)

        infill = np.reshape(infill, (-1, 3))

        c = np.cos(infill_angle)
        s = np.sin(infill_angle)
        rotation_matrix = np.array([[c, -s, 0],
                                    [s, c, 0],
                                    [0, 0, 1]])

        translation_matrix = np.array([[1, 0, 0],
                                       [0, 1, 0],
                                       [x0, y0, 1]])

        infill = np.matmul(infill, rotation_matrix)
        infill = np.matmul(infill, translation_matrix)
        infill = np.reshape(infill, (-1, 2, 3))

        pc.AddPaths(infill, pyclipper.PT_SUBJECT, False)

        # Clip infill lines
        # (Open paths will be returned as NodeTree, so we have to use PyClipper.Execute2() here)
        solution = pc.Execute2(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)

        if solution.depth > 0:
            assert solution.depth == 1, \
                f"PyClipper.Execute2() returned solution with depth != 1 ({solution.depth})"

            for child in solution.Childs:
                result.append(child.Contour)

    return result
