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

import numpy

VERTEX_PRECISION = 1000.0


class Vertex:
    def __init__(self, x, y, z, flag):
        self.x = x
        self.y = y
        self.z = z
        self.flag = flag

    def __str__(self):
        return "Vertex(%s, %s, %s)(%s)" % (self.x, self.y, self.z, self.flag)


class Edge:
    def __init__(self, p, q):
        self.p = p
        self.q = q

    def get_point_at_z(self, z):
        """
        Calculates point at z between p and q
        :param z: z
        :return: Calculated point as tuple(x, y)
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
        #     x3 = z, p3 = p.z, u3 = q.z - p.z
        #
        # s can be calculated
        #     s = (z - p.z) / (q.z - p.z)

        s = (z - self.p.z) / (self.q.z - self.p.z)

        return int(self.p.x + s * (self.q.x - self.p.x)), \
            int(self.p.y + s * (self.q.y - self.p.y))

    def __str__(self):
        return "Edge(%s, %s)" % (self.p, self.q)


class Triangle:
    def __init__(self, v1, v2, v3, n):
        """
        :param v1: numpy.array([x1, y1, z1])
        :param v2: numpy.array([x2, y2, z2])
        :param v3: numpy.array([x3, y3, z3])
        :param n: numpy.array([x, y, z])
        """
        # https://en.wikipedia.org/wiki/Back-face_culling
        if numpy.dot(-v1, n) < 0 and not numpy.array_equal(n, [0, 1, 0]):
            self.v1 = Vertex(*v1, 0)
            self.v2 = Vertex(*v2, 1)
            self.v3 = Vertex(*v3, 2)
        else:
            self.v1 = Vertex(*v1, 2)
            self.v2 = Vertex(*v2, 1)
            self.v3 = Vertex(*v3, 0)

        if self.v1.z >= self.v2.z >= self.v3.z:
            self.z_max, self.z_med, self.z_min = self.v1, self.v2, self.v3
        elif self.v1.z >= self.v3.z >= self.v2.z:
            self.z_max, self.z_med, self.z_min = self.v1, self.v3, self.v2
        elif self.v2.z >= self.v1.z >= self.v3.z:
            self.z_max, self.z_med, self.z_min = self.v2, self.v1, self.v3
        elif self.v2.z >= self.v3.z >= self.v1.z:
            self.z_max, self.z_med, self.z_min = self.v2, self.v3, self.v1
        elif self.v3.z >= self.v1.z >= self.v2.z:
            self.z_max, self.z_med, self.z_min = self.v3, self.v1, self.v2
        elif self.v3.z >= self.v2.z >= self.v1.z:
            self.z_max, self.z_med, self.z_min = self.v3, self.v2, self.v1

        self.s1 = Edge(self.z_min, self.z_max)
        self.s2 = Edge(self.z_min, self.z_med)
        self.s3 = Edge(self.z_med, self.z_max)

    def get_forward_edge(self):
        if self.z_min.flag == 0:
            if self.z_max.flag == 1:
                return self.s2, self.s3
            elif self.z_max.flag == 2:
                return self.s1, self.s1
        elif self.z_min.flag == 1:
            if self.z_max.flag == 0:
                return self.s1, self.s1
            elif self.z_max.flag == 2:
                return self.s2, self.s3
        elif self.z_min.flag == 2:
            if self.z_max == 0:
                return self.s2, self.s3
            elif self.z_max == 1:
                return self.s1, self.s1

    def slice(self, first_layer_height, layer_height):
        start = max(0, math.floor((self.z_min.z - first_layer_height) / layer_height) + 1)
        middle = math.floor((self.z_med.z - first_layer_height) / layer_height) + 1
        end = math.floor((self.z_max.z - first_layer_height) / layer_height) + 1

        forward_edge1, forward_edge2 = self.get_forward_edge()

        for layer in range(start, middle):
            z = first_layer_height + layer * layer_height
            x, y = forward_edge1.get_point_at_z(z)
            # TODO

        for layer in range(middle, end):
            z = first_layer_height + layer * layer_height
            x, y = forward_edge2.get_point_at_z(z)
            # TODO

    def __str__(self):
        return "Triangle(%s, %s, %s)" % (self.z_min, self.z_med, self.z_max)


class Slicer:
    def __init__(self, model):
        """
        :param model: Instance of model.Model
        """
        self.model = model

        # center model and set its z_min to 0
        t = numpy.array([-(model.bounding_box.x_max+model.bounding_box.x_min) / 2,
                         -(model.bounding_box.y_max+model.bounding_box.y_min) / 2,
                         -model.bounding_box.z_min], numpy.float32)

        vertices = numpy.add(model.vertices, t)
        vertices = numpy.multiply(vertices, VERTEX_PRECISION)
        self.vertices = vertices.astype(numpy.int32)

        self.normals = model.normals.astype(numpy.int32)

        self.indices = model.indices.reshape((-1, 3))  # Done to make iterating in chunks easier

    def slice(self, first_layer_height, layer_height):
        """
        :param first_layer_height: in mm (e.g. 0.3)
        :param layer_height: in mm (e.g. 0.2)
        :return: Instance of SlicedModel
        """
        first_layer_height = int(first_layer_height * VERTEX_PRECISION)
        layer_height = int(layer_height * VERTEX_PRECISION)

        sliced_model = []
        for i, j, k in self.indices:
            v1, v2, v3 = self.vertices[i], self.vertices[j], self.vertices[k]
            n = self.normals[i]  # all normals of a face are the same

            triangle = Triangle(v1, v2, v3, n)

            if triangle.z_min == triangle.z_max:
                continue

            print(triangle)

