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
import enum

import numpy


class BoundingBox:
    def __init__(self):
        self.x_min = self.y_min = self.z_min = float("inf")
        self.x_max = self.y_max = self.z_max = -float("inf")

    def update(self, vertex):
        self.x_min = min(vertex[0], self.x_min)
        self.x_max = max(vertex[0], self.x_max)
        self.y_min = min(vertex[1], self.y_min)
        self.y_max = max(vertex[1], self.y_max)
        self.z_min = min(vertex[2], self.z_min)
        self.z_max = max(vertex[2], self.z_max)

    def center(self):
        return numpy.array([(self.x_max-self.x_min)/2,
                            (self.y_max-self.y_min)/2,
                            (self.z_max-self.z_min)/2])

    def diagonal(self):
        return numpy.subtract(numpy.array([self.x_min, self.y_min, self.z_min]),
                              numpy.array([self.x_max, self.y_max, self.z_max]))

    def copy(self):
        result = BoundingBox()
        result.x_min = self.x_min
        result.x_max = self.x_max
        result.y_min = self.y_min
        result.y_max = self.y_max
        result.z_min = self.z_min
        result.z_max = self.z_max

        return result

    def __str__(self):
        return """Bounding box:
    x: %s, %s
    y: %s, %s
    z: %s, %s
        """ % (self.x_min, self.x_max, self.y_min, self.y_max, self.z_min, self.z_max)


StlParserState = enum.Enum("StlParserState",
                           "START SOLID FACET_NORMAL OUTER_LOOP VERTEX1 VERTEX2 VERTEX3 ENDLOOP ENDFACET ENDSOLID")


class StlParserError(RuntimeError):
    def __init__(self, filename, line_no, msg):
        RuntimeError.__init__(self, "File '%s', line %s: %s" % (filename, line_no, msg))


class StlAsciiFileParser:
    def __init__(self, filename):
        self.filename = filename
        self.ln_no = 1
        self.parser_state = StlParserState.START

        self.normal = None
        self.vertex1 = None
        self.vertex2 = None
        self.vertex3 = None

        self.bb = BoundingBox()

        self.vertices = collections.OrderedDict()  # key: (vertex, normal), value: index
        self.indices = []
        self.index = 0

    @staticmethod
    def _parse_vertex(line):
        data = line.split(" ")[1:]
        assert len(data) == 3, "Vertex requires 3 elements"
        return float(data[0]), float(data[1]), float(data[2])

    def parse(self):
        states = {StlParserState.START: self._do_start,
                  StlParserState.SOLID: self._do_solid,
                  StlParserState.ENDFACET: self._do_solid,
                  StlParserState.FACET_NORMAL: self._do_facet_normal,
                  StlParserState.OUTER_LOOP: self._do_outer_loop,
                  StlParserState.VERTEX1: self._do_vertex1,
                  StlParserState.VERTEX2: self._do_vertex2,
                  StlParserState.VERTEX3: self._do_vertex3,
                  StlParserState.ENDLOOP: self._do_endloop}

        with open(self.filename, "r") as f:
            for line in f:
                ln = line.strip()

                if not states[self.parser_state](ln):
                    break

                self.ln_no += 1

            return numpy.array([k[0] for k, v in self.vertices.items()], numpy.float32), \
                numpy.array([k[1] for k, v in self.vertices.items()], numpy.float32), \
                numpy.array(self.indices, numpy.uint32), self.bb

    def _do_start(self, ln):
        assert ln.startswith("solid"), "Expected keyword 'solid'"
        self.parser_state = StlParserState.SOLID

        return True

    def _do_solid(self, ln):
        assert ln.startswith("facet normal") or ln.startswith("endsolid"), "Expected keyword 'facet normal'"

        if ln.startswith("facet normal"):
            self.parser_state = StlParserState.FACET_NORMAL

            data = ln.split(" ")[2:]
            assert len(data) == 3, "Normal requires 3 elements"
            self.normal = float(data[0]), float(data[1]), float(data[2])

            return True

        if ln.startswith("endsolid"):
            return False

    def _do_facet_normal(self, ln):
        assert ln == "outer loop", "Expected keyword 'outer loop'"
        self.parser_state = StlParserState.OUTER_LOOP

        return True

    def _do_outer_loop(self, ln):
        assert ln.startswith("vertex"), "Expected keyword 'vertex'"

        self.parser_state = StlParserState.VERTEX1
        self.vertex1 = self._parse_vertex(ln)

        return True

    def _do_vertex1(self, ln):
        assert ln.startswith("vertex"), "Expected keyword 'vertex'"

        self.parser_state = StlParserState.VERTEX2
        self.vertex2 = self._parse_vertex(ln)

        return True

    def _do_vertex2(self, ln):
        assert ln.startswith("vertex"), "Expected keyword 'vertex'"

        self.parser_state = StlParserState.VERTEX3
        self.vertex3 = self._parse_vertex(ln)

        return True

    def _do_vertex3(self, ln):
        assert ln == "endloop", "Expected keyword 'endloop'"

        self.parser_state = StlParserState.ENDLOOP

        self._add_vertex(self.vertex1, self.normal)
        self._add_vertex(self.vertex2, self.normal)
        self._add_vertex(self.vertex3, self.normal)

        self.bb.update(self.vertex1)
        self.bb.update(self.vertex2)
        self.bb.update(self.vertex3)

        return True

    def _add_vertex(self, v, n):
        try:
            self.indices.append(self.vertices[(v, n)])
        except KeyError:
            self.vertices[(v, n)] = self.index
            self.indices.append(self.index)
            self.index += 1

    def _do_endloop(self, ln):
        assert ln == "endfacet", "Expected keyword 'endfacet'"
        self.parser_state = StlParserState.ENDFACET

        return True


if __name__ == "__main__":
    parser = StlAsciiFileParser("cube.stl")
    vertices, normals, indices, bb = parser.parse()

    print(len(vertices), vertices)
    print(len(normals), normals)
    print(len(indices), indices)
    print(bb)
