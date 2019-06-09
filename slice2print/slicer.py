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


class Slicer:
    def __init__(self, vertices, normals, indices):
        """
        :param vertices: numpy.array() containing the vertices
        :param normals: numpy.array() containing the normals
        :param indices:  numpy.array() containing the indices
        """
        self.vertices = vertices
        self.normals = normals
        self.indices = indices.reshape((-1, 3))  # Done to make iterating in chunks easier

    def slice(self, layer_height):
        """
        :param layer_height: in mm (e.g. 0.2)
        :return: Lists segments [((x1, y1, z1), (x2, y2, z1)), ((x3, y3, z2), (x4, y4, z2)), ...]
        """
        segments = []

        for i, j, k in self.indices:
            v1, v2, v3 = self.vertices[i], self.vertices[j], self.vertices[k]

            z_min = min(v3[2], min(v2[2], min(v1[2], float("Inf"))))
            z_max = max(v3[2], max(v2[2], max(v1[2], -float("Inf"))))

            z_min = math.floor(z_min / layer_height) * layer_height
            z_max = math.ceil(z_max / layer_height) * layer_height

            steps = int((z_max - z_min) / layer_height)

            for s in range(1, steps+1):
                z = z_min + s * layer_height

                points = self._find_intersection_points(v1, v2, v3, z)

                if len(points) == 2:
                    segments.append(points)

        return segments

    def _find_intersection_points(self, v1, v2, v3, z):
        """
        :param v1: 1st vertex of triangle
        :param v2: 2nd vertex of triangle
        :param v3: 3rd vertex of triangle
        :param z: z-height
        :return: List of points [(x1, y1, z), (x2, y2, z), ...]
        """
        points = []

        if v1[2] < z < v2[2] or v1[2] > z > v2[2]:
            points.append(self._get_point_at_z(v1, v2, z))

        if v1[2] < z < v3[2] or v1[2] > z > v3[2]:
            points.append(self._get_point_at_z(v1, v3, z))

        if v2[2] < z < v3[2] or v2[2] > z > v3[2]:
            points.append(self._get_point_at_z(v2, v3, z))

        if math.isclose(v1[2], z):
            points.append(tuple(v1))

        if math.isclose(v2[2], z):
            points.append(tuple(v2))

        if math.isclose(v3[2], z):
            points.append(tuple(v3))

        return points

    @staticmethod
    def _get_point_at_z(p, q, z):
        """
        Calculates point at z between p and q
        :param p: Vector P as tuple (x, y, z)
        :param q: Vector Q as tuple (x, y, z)
        :param z: z as float
        :return: Calculated point as tuple (x, y, z)
        """
        # Vector form of the equation of a line
        #     X = P + s * U with U = Q - P
        #
        # Parametric from of the equation of a line
        #     x1 = p1 + s * u1 with u1 = q1 - p1
        #     x2 = p2 + s * u2 with u2 = q2 - p2
        #     x3 = p3 + s * u3 with u3 = q3 - p3
        #
        # Known values for variables
        #     x3 = z, p3 = p[2], u3 = q[2] - p[2]
        #
        # s can be calculated
        #     s = (z - p[2]) / (q[2] - p[2])

        s = (z - p[2]) / (q[2] - p[2])

        return (p[0] + s * (q[0] - p[0]),
                p[1] + s * (q[1] - p[1]),
                z)
