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


class Vertex:
    def __init__(self, x, y, z, flag=None):
        self.x = x
        self.y = y
        self.z = z
        self.flag = flag

    def __eq__(self, other):
        # We don't care about the flag here
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __str__(self):
        return "Vertex(x: %s, y: %s, z: %s, flag: %s)" % (self.x, self.y, self.z, self.flag)


class Edge:
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

    def __eq__(self, other):
        return self.p == other.p and self.q == other.q

    def __str__(self):
        return "Edge(p: %s, q: %s)" % (self.p, self.q)


class Intersection:
    """
    Contains the intersection of a z plane with a triangle
    and the two edges of the triangle which were intersected
    """
    def __init__(self, v_inter, forward_edge, backward_edge, layer):
        self.v_inter = v_inter
        self.forward_edge = forward_edge
        self.backward_edge = backward_edge
        self.layer = layer

    def __str__(self):
        return "Intersection(v_inter: %s, layer: %s)" % (self.v_inter, self.layer)


class Triangle:
    def __init__(self, v1, v2, v3, n):
        """
        :param v1: numpy.array([x1, y1, z1])
        :param v2: numpy.array([x2, y2, z2])
        :param v3: numpy.array([x3, y3, z3])
        :param n: numpy.array([x, y, z])
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

    def __str__(self):
        return """Triangle(
    lower forward edge: %s,
    upper forward edge: %s,
    lower backward edge: %s,
    upper backward edge: %s)""" % self.get_forward_edge()


class IntersectionList:
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

    def add_to_front(self, intersections):
        self.intersections.extendleft(reversed(intersections.intersections))

    def add_to_back(self, intersections):
        self.intersections.extend(intersections.intersections)

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


class ContourList:
    """
    Contains the contour of one layer
    """
    def __init__(self):
        self.contour = collections.deque()

    def add(self, intersection):
        for intersection_list in self.contour:
            if intersection_list.add_to_front_if_adjacent(intersection):
                self.add_to_back_if_adjacent(intersection_list)
                break
            elif intersection_list.add_to_back_if_adjacent(intersection):
                self.add_to_front_if_adjacent(intersection_list)
                break
        else:
            # intersection was not added to an existing intersection list so create a new one
            self.contour.append(IntersectionList(intersection))

    def add_to_back_if_adjacent(self, intersection_list):
        intersection = intersection_list.first

        for contour_part in self.contour:
            if contour_part == intersection_list:
                continue

            if contour_part.is_adjacent_to_last_element(intersection):
                contour_part.add_to_back(intersection_list)
                self.contour.remove(intersection_list)
                break

    def add_to_front_if_adjacent(self, intersection_list):
        intersection = intersection_list.last

        for contour_part in self.contour:
            if contour_part == intersection_list:
                continue

            if contour_part.is_adjacent_to_first_element(intersection):
                contour_part.add_to_front(intersection_list)
                self.contour.remove(intersection_list)
                break

    def __str__(self):
        return "Contour(# of intersection lists: %s)" % len(self.contour)


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
        :return: TODO
        """
        slice_count = math.floor((self.model.dimensions.z - first_layer_height) / layer_height + 1)

        first_layer_height = int(first_layer_height * VERTEX_PRECISION)
        layer_height = int(layer_height * VERTEX_PRECISION)

        slices = []
        for intersection in range(slice_count):
            slices.append(ContourList())

        for intersection, j, k in self.indices:
            v1, v2, v3 = self.vertices[intersection], self.vertices[j], self.vertices[k]
            n = self.normals[intersection]  # all normals of a face are the same

            triangle = Triangle(v1, v2, v3, n)

            if triangle.vz_min.z != triangle.vz_max.z:
                for intersection in triangle.slice(first_layer_height, layer_height):
                    slices[intersection.layer].add(intersection)

        sliced_model = []
        for slice in slices:
            for contour in slice.contour:
                p1 = p2 = None

                for intersection in contour.intersections:
                    if p1 is None:
                        p1 = intersection
                    elif p2 is None:
                        p2 = intersection
                    else:
                        p1 = p2
                        p2 = intersection

                    if p1 is not None and p2 is not None:
                        sliced_model.append([[*p1.v_inter], [*p2.v_inter]])

                if len(slice.contour[0].intersections) > 2:
                    sliced_model.append([[*slice.contour[0].first.v_inter],
                                         [*slice.contour[0].last.v_inter]])

        return sliced_model


if __name__ == "__main__":
    import model

    m = model.Model.from_file("../test.stl")
    s = Slicer(m)
    print(s.slice(0.3, 0.2))
