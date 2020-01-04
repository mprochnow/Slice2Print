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

# Implementation of "An improved slicing algorithm with efficient contour
# construction using STL files" by Zhengyan Zhang and Sanjay Joshi

import collections
import math

import numpy

from .sliced_model import SlicedModel


class Vertex:
    __slots__ = ["x", "y", "z", "flag"]

    def __init__(self, x, y, z, flag=None):
        self.x = x
        self.y = y
        self.z = z
        self.flag = flag

    def __eq__(self, other):
        # We don't care about the flag here
        return self.x == other.x and self.y == other.y and self.z == other.z


class Edge:
    __slots__ = ["p", "q"]

    def __init__(self, p, q):
        """
        :param p: Instance of Vertex
        :param q: Instance of Vertex
        """
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
        # Parametric form of the equation of a line
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

    def __eq__(self, other):
        return self.p == other.p and self.q == other.q


class Intersection:
    """
    Contains the intersection of a z plane with a triangle
    and the two edges of the triangle which were intersected
    """
    __slots__ = ["vertex", "forward_edge", "backward_edge", "layer"]

    def __init__(self, vertex, forward_edge, backward_edge, layer):
        self.vertex = vertex
        self.forward_edge = forward_edge
        self.backward_edge = backward_edge
        self.layer = layer

    @property
    def xy(self):
        return self.vertex.x, self.vertex.y


class Triangle:
    __slots__ = ["v1", "v2", "v3", "vz_min", "vz_med", "vz_max", "s1", "s2", "s3"]

    def __init__(self, v1, v2, v3):
        """
        :param v1: numpy.array([x1, y1, z1])
        :param v2: numpy.array([x2, y2, z2])
        :param v3: numpy.array([x3, y3, z3])
        """
        self.v1 = Vertex(*v1, 0)
        self.v2 = Vertex(*v2, 1)
        self.v3 = Vertex(*v3, 2)

        if self.v1.z >= self.v2.z >= self.v3.z:
            self.vz_max, self.vz_med, self.vz_min = self.v1, self.v2, self.v3
        elif self.v1.z >= self.v3.z >= self.v2.z:
            self.vz_max, self.vz_med, self.vz_min = self.v1, self.v3, self.v2
        elif self.v2.z >= self.v1.z >= self.v3.z:
            self.vz_max, self.vz_med, self.vz_min = self.v2, self.v1, self.v3
        elif self.v2.z >= self.v3.z >= self.v1.z:
            self.vz_max, self.vz_med, self.vz_min = self.v2, self.v3, self.v1
        elif self.v3.z >= self.v1.z >= self.v2.z:
            self.vz_max, self.vz_med, self.vz_min = self.v3, self.v1, self.v2
        elif self.v3.z >= self.v2.z >= self.v1.z:
            self.vz_max, self.vz_med, self.vz_min = self.v3, self.v2, self.v1

        self.s1 = Edge(self.vz_min, self.vz_max)
        self.s2 = Edge(self.vz_min, self.vz_med)
        self.s3 = Edge(self.vz_med, self.vz_max)

    def get_forward_edge(self):
        """
        :return: tuple (lower forward edge, upper forward edge, lower backward edge, upper backward edge)
        """

        if self.vz_min.flag == 0:
            if self.vz_max.flag == 1:
                return self.s2, self.s3, self.s1, self.s1
            elif self.vz_max.flag == 2:
                return self.s1, self.s1, self.s2, self.s3
        elif self.vz_min.flag == 1:
            if self.vz_max.flag == 0:
                return self.s1, self.s1, self.s2, self.s3
            elif self.vz_max.flag == 2:
                return self.s2, self.s3, self.s1, self.s1
        elif self.vz_min.flag == 2:
            if self.vz_max.flag == 0:
                return self.s2, self.s3, self.s1, self.s1
            elif self.vz_max.flag == 1:
                return self.s1, self.s1, self.s2, self.s3

    def slice(self, first_layer_height, layer_height):
        """
        Yields for each z plane intersection an instance of Intersection
        """
        start = max(0, math.floor((self.vz_min.z - first_layer_height) / layer_height) + 1)
        middle = max(0, math.floor((self.vz_med.z - first_layer_height) / layer_height) + 1)
        end = max(0, math.floor((self.vz_max.z - first_layer_height) / layer_height) + 1)

        lower_forward_edge, upper_forward_edge, lower_backward_edge, upper_backward_edge = self.get_forward_edge()

        for layer in range(start, middle):
            z = first_layer_height + layer * layer_height
            x, y = lower_forward_edge.get_point_at_z(z)

            yield Intersection(Vertex(x, y, z), lower_forward_edge, lower_backward_edge, layer)

        for layer in range(middle, end):
            z = first_layer_height + layer * layer_height
            x, y = upper_forward_edge.get_point_at_z(z)

            yield Intersection(Vertex(x, y, z), upper_forward_edge, upper_backward_edge, layer)


class Intersections:
    """
    Contains the intersections of one layer
    """
    def __init__(self, first):
        self.intersections = collections.deque()
        self.intersections.append(first)

    @property
    def first(self):
        return self.intersections[0]

    @property
    def last(self):
        return self.intersections[-1]

    @property
    def closed(self):
        return self.last.backward_edge == self.first.forward_edge

    def is_adjacent_to_first_element(self, intersection):
        """
        :param intersection: Instance if Intersection
        :return: True if backward edge of intersection is adjacent to forward edge of first element
        """
        return intersection.backward_edge == self.first.forward_edge

    def is_adjacent_to_last_element(self, intersection):
        """
        :param intersection: Instance of Intersection
        :return: True if forward edge of intersection is adjacent to backward edge of last element
        """
        return intersection.forward_edge == self.last.backward_edge

    def add_to_front_if_adjacent(self, intersection):
        """
        If intersection is adjacent to first element, intersection is added as new first element
        :param intersection: Instance of Intersection
        :return: True if intersection was added
        """
        result = self.is_adjacent_to_first_element(intersection)
        if result:
            self.intersections.appendleft(intersection)

        return result

    def add_to_back_if_adjacent(self, intersection):
        """
        If intersection is adjacent to last element, intersection is added as new last element
        :param intersection: Instance of Intersection
        :return: True if intersection was added
        """
        result = self.is_adjacent_to_last_element(intersection)
        if result:
            self.intersections.append(intersection)

        return result

    def add_intersections_to_front(self, intersections):
        """
        :param intersections: Instance of Intersections
        """
        self.intersections.extendleft(reversed(intersections.intersections))

    def add_intersections_to_back(self, intersections):
        """
        :param intersections: Instance of Intersections
        """
        self.intersections.extend(intersections.intersections)

    def __iter__(self):
        yield from self.intersections

    def __len__(self):
        return len(self.intersections)


class Contour:
    """
    Contains the contour of one layer
    """
    def __init__(self, z):
        self.contour = collections.deque()
        self.z = z

    def add(self, intersection):
        """
        :param intersection: Instance of Intersection
        """
        for intersections in self.contour:
            if intersections.add_to_front_if_adjacent(intersection):
                self.add_to_back_if_adjacent(intersections)
                break
            elif intersections.add_to_back_if_adjacent(intersection):
                self.add_to_front_if_adjacent(intersections)
                break
        else:
            # intersection was not added to an existing intersection list so create a new one
            self.contour.append(Intersections(intersection))

    def add_to_back_if_adjacent(self, intersections_to_add):
        """
        :param intersections_to_add: Instance of Intersections
        """
        for intersections in self.contour:
            if intersections == intersections_to_add:
                continue

            if intersections.is_adjacent_to_last_element(intersections_to_add.first):
                intersections.add_intersections_to_back(intersections_to_add)
                self.contour.remove(intersections_to_add)
                break

    def add_to_front_if_adjacent(self, intersections_to_add):
        """
        :param intersections_to_add: Instance of Intersections
        """
        for intersections in self.contour:
            if intersections == intersections_to_add:
                continue

            if intersections.is_adjacent_to_first_element(intersections_to_add.last):
                intersections.add_intersections_to_front(intersections_to_add)
                self.contour.remove(intersections_to_add)
                break

    def __iter__(self):
        yield from self.contour


class Slicer:
    def __init__(self, slicer_config, model, update_func=None):
        """
        :param slicer_config: Instance of SlicerConfig
        :param model: Instance of model.Model
        :param update_func: Function to call to indicate progress
        """
        self.cancelled = False
        self.slicer_config = slicer_config
        self.model = model
        self.update_func = update_func
        self.first_layer_height = int(slicer_config.first_layer_height * slicer_config.VERTEX_PRECISION)
        self.layer_height = int(slicer_config.layer_height * slicer_config.VERTEX_PRECISION)

        self.update_interval = max(1, self.model.facet_count // 100)

        self.layer_count = math.floor((self.model.dimensions.z - slicer_config.first_layer_height) /
                                      slicer_config.layer_height + 1)
        self.contours = []
        for i in range(self.layer_count):
            z = self.first_layer_height + i * self.layer_height
            self.contours.append(Contour(z))

        # center model and set its z_min to 0
        t = numpy.array([-(model.bounding_box.x_max+model.bounding_box.x_min) / 2,
                         -(model.bounding_box.y_max+model.bounding_box.y_min) / 2,
                         -model.bounding_box.z_min], numpy.float32)

        vertices = numpy.add(model.vertices, t)
        vertices = numpy.multiply(vertices, slicer_config.VERTEX_PRECISION)
        self.vertices = vertices.astype(numpy.int32)

        # Reshape indices list to make iterating in chunks easier
        self.indices = model.indices.reshape((-1, 3))

    def slice(self):
        """
        :return: Instance of SlicedModel if not cancelled else None
        """
        triangle_no = 0
        for i, j, k in self.indices:
            triangle_no += 1
            v1, v2, v3 = self.vertices[i], self.vertices[j], self.vertices[k]

            triangle = Triangle(v1, v2, v3)

            if triangle.vz_min.z != triangle.vz_max.z:
                for intersection in triangle.slice(self.first_layer_height, self.layer_height):
                    self.contours[intersection.layer].add(intersection)

                if self.update_func is not None and triangle_no % self.update_interval == 0:
                    msg = "%s/%s triangles sliced" % (triangle_no, self.model.facet_count)

                    self.cancelled = self.update_func(int(triangle_no / self.model.facet_count * 100), msg)
                    if self.cancelled:
                        return None

        return SlicedModel(self.slicer_config, self.model.bounding_box, self.contours)
