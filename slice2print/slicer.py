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

import collections
import math

import numpy

VERTEX_PRECISION = 1000.0


class Point2D:
    __slots__ = ['x', 'y']

    def __init__(self, x, y, _=None):
        self.x = x
        self.y = y

    def __str__(self):
        return "Point2D(%s, %s)" % (self.x, self.y)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __iter__(self):
        yield self.x
        yield self.y


class Segment2D:
    __slots__ = ['p1', 'p2']

    def __init__(self, p1, p2):
        self.p1 = p1
        self.p2 = p2

    def __str__(self):
        return "Segment2D(%s - %s)" % (self.p1, self.p2)


class Polygon2D:
    def __init__(self):
        self.points = []
        self.closed = False

    def add_point(self, point):
        self.points.append(point)

    def __len__(self):
        return len(self.points)

    def __str__(self):
        return "Polygon2D(%s)" % ", ".join([str(p) for p in self.points])


class Layer:
    def __init__(self):
        self.segments = collections.deque()
        self.polygons = []

    def add_segment(self, segment):
        self.segments.append(segment)

    def make_polygons(self):
        while len(self.segments):
            polygon = Polygon2D()

            segment = self.segments.popleft()
            polygon.add_point(segment.p1)
            polygon.add_point(segment.p2)

            p = segment.p2

            while p is not None:
                for segment in self.segments:
                    if segment.p1 == p:
                        p = segment.p2
                        polygon.add_point(p)

                        self.segments.remove(segment)
                        break

                    if segment.p2 == p:
                        p = segment.p1
                        polygon.add_point(p)

                        self.segments.remove(segment)
                        break
                else:
                    p = None

            if len(polygon) > 3:
                if polygon.points[0] == polygon.points[-1]:
                    polygon.closed = True

                self.polygons.append(polygon)

    def __iter__(self):
        yield from self.segments


class SlicedModel:
    def __init__(self, model_height, first_layer_height, layer_height):
        self.first_layer_height = first_layer_height
        self.layer_height = layer_height

        layer_count = int((model_height - first_layer_height) / layer_height) + 1
        self.layers = [Layer() for _ in range(layer_count)]

    def add_segment_to_layer(self, segment, layer):
        self.layers[layer].add_segment(segment)

    def raw_data(self):
        """
        :return: Lists segments [((x1, y1, z1), (x2, y2, z1)), ((x3, y3, z2), (x4, y4, z2)), ...]
        """
        result = []

        for i, layer in enumerate(self.layers):
            layer.make_polygons()

            z = self.first_layer_height + i * self.layer_height

            for polygon in layer.polygons:
                p1 = p2 = None
                for p in polygon.points:
                    if p1 is None:
                        p1 = p
                    elif p2 is None:
                        p2 = p
                    else:
                        p1 = p2
                        p2 = p

                    if p1 is not None and p2 is not None:
                        result.append([[*p1, z],
                                       [*p2, z]])

        return result


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

        self.indices = model.indices.reshape((-1, 3))  # Done to make iterating in chunks easier

    def slice(self, first_layer_height, layer_height):
        """
        :param first_layer_height: in mm (e.g. 0.3)
        :param layer_height: in mm (e.g. 0.2)
        :return: Instance of SlicedModel
        """
        first_layer_height = int(first_layer_height * VERTEX_PRECISION)
        layer_height = int(layer_height * VERTEX_PRECISION)

        sliced_model = SlicedModel(self.model.dimensions()[2] * VERTEX_PRECISION,
                                   first_layer_height, layer_height)

        for i, j, k in self.indices:
            v1, v2, v3 = self.vertices[i], self.vertices[j], self.vertices[k]

            z_min = min(v3[2], min(v2[2], v1[2]))
            z_max = max(v3[2], max(v2[2], v1[2]))

            start = max(0, math.floor((z_min - first_layer_height) / layer_height) + 1)
            end = math.floor((z_max - first_layer_height) / layer_height) + 1

            for layer in range(start, end):
                z = first_layer_height + layer * layer_height

                points = self._find_intersection_points(v1, v2, v3, z)

                if len(points) == 2:
                    sliced_model.add_segment_to_layer(Segment2D(*points), layer)

        return sliced_model

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

        if v1[2] == z:
            points.append(Point2D(*v1))

        if v2[2] == z:
            points.append(Point2D(*v2))

        if v3[2] == z:
            points.append(Point2D(*v3))

        return points

    @staticmethod
    def _get_point_at_z(p, q, z):
        """
        Calculates point at z between p and q
        :param p: Vector P as tuple (px, py, pz)
        :param q: Vector Q as tuple (qx, qy, qz)
        :param z: z
        :return: Calculated point as Point2D(x, y)
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

        return Point2D(int(p[0] + s * (q[0] - p[0])),
                       int(p[1] + s * (q[1] - p[1])))
