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

from OpenGL.GL import *
import numpy.linalg

from ui.glhelpers import GlBuffer, rotate_x, ShaderProgram
from ui import glmesh

numpy.seterr(all="raise")


# 4 quads à 4 vertices
VERTICES_PER_LINE = 4 * 4
INDEX_ARRAYS_PER_LINE = 4

# 2 triangles à 3 vertices
VERTICES_PER_CORNER = 2 * 3
INDEX_ARRAYS_PER_CORNER = 1

VERTICES_PER_NODE = VERTICES_PER_LINE + VERTICES_PER_CORNER
NORMALS_PER_NODE = VERTICES_PER_NODE
INDEX_ARRAYS_PER_NODE = INDEX_ARRAYS_PER_LINE + INDEX_ARRAYS_PER_CORNER


class LayerMesh:
    def __init__(self, sliced_model):
        self.initialized = False
        self.program = None
        self.vertex_buffer = None
        self.normal_buffer = None
        self.index_buffer = None
        self.vao = None

        self.sliced_model = sliced_model
        self.bounding_box = sliced_model.bounding_box
        self.layer_count = sliced_model.layer_count
        self.layers_to_draw = sliced_model.layer_count

        self.vertices_count_at_layer = []

        self.model_color = numpy.array([1.0, 0.5, 0.0, 1.0], numpy.float32)
        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)

        # OpenGL z-axis points in a different direction, so we have to flip the model
        self.model_matrix = rotate_x(-90)

    def init(self):
        self.initialized = True

        v, n, i = self.create_mesh()

        self.program = ShaderProgram(glmesh.MODEL_VERTEX_SHADER, glmesh.BASIC_FRAGMENT_SHADER)
        self.vertex_buffer = GlBuffer(v, GL_ARRAY_BUFFER)
        self.normal_buffer = GlBuffer(n, GL_ARRAY_BUFFER)
        self.index_buffer = GlBuffer(i, GL_ELEMENT_ARRAY_BUFFER)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vertex_position_index = self.program.get_attrib_location("vertex_position")
        vertex_normal_index = self.program.get_attrib_location("vertex_normal")

        with self.vertex_buffer:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

        with self.normal_buffer:
            glVertexAttribPointer(vertex_normal_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_normal_index)

        with self.program:
            self.program.model_color = self.model_color
            self.program.model_matrix = self.model_matrix
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

    def create_mesh(self):
        # Arrays will be created with needed size, this avoids expensive allocation and copy operations
        vertices = numpy.zeros((self.sliced_model.node_count * VERTICES_PER_NODE, 3), numpy.float32)
        normals = numpy.zeros((self.sliced_model.node_count * NORMALS_PER_NODE, 3), numpy.float32)
        indices = numpy.zeros((self.sliced_model.node_count * INDEX_ARRAYS_PER_NODE, 6), numpy.uint32)

        p2m = PathToMesh(self.sliced_model.cfg)
        l2m = LinesToMesh(self.sliced_model.cfg)

        node_count = 0
        for layer_no, layer in enumerate(self.sliced_model.layers):
            for perimeter_no, perimeter in enumerate(layer.perimeters):
                for path in perimeter:
                    # Slicer worked with integers, needs to be reverted
                    # Also, append first node of path to its end to close it
                    # (assuming that a perimeter ist a closed loop, this might change in the future)
                    path_ = numpy.divide(path + [path[0]], self.sliced_model.cfg.VERTEX_PRECISION)
                    path_length = len(path_) - 1

                    start = node_count
                    end = node_count + path_length

                    v = vertices[start * VERTICES_PER_NODE:end * VERTICES_PER_NODE]
                    n = normals[start * NORMALS_PER_NODE:end * NORMALS_PER_NODE]
                    i = indices[start * INDEX_ARRAYS_PER_NODE:end * INDEX_ARRAYS_PER_NODE]

                    p2m.create_mesh(v, n, i, path_, perimeter_no == 0, layer_no)

                    i += node_count * VERTICES_PER_NODE

                    node_count += path_length

            if len(layer.infill):
                lines_length = 2 * len(layer.infill)

                start = node_count
                end = node_count + lines_length

                v = vertices[start * VERTICES_PER_NODE:end * VERTICES_PER_NODE]
                n = normals[start * NORMALS_PER_NODE:end * NORMALS_PER_NODE]
                i = indices[start * INDEX_ARRAYS_PER_NODE:end * INDEX_ARRAYS_PER_NODE]

                l2m.create_mesh(v,
                                n,
                                i,
                                numpy.divide(layer.infill, self.sliced_model.cfg.VERTEX_PRECISION),
                                layer_no)

                i += node_count * VERTICES_PER_NODE

                node_count += lines_length

            self.vertices_count_at_layer.append(node_count * INDEX_ARRAYS_PER_NODE * 6)

        return vertices.ravel(), normals.ravel(), indices.ravel()

    def delete(self):
        self.vertex_buffer.delete()
        self.normal_buffer.delete()
        self.index_buffer.delete()
        glDeleteVertexArrays(1, [self.vao])

    def update_view_matrix(self, matrix):
        self.view_matrix = matrix

    def update_projection_matrix(self, matrix):
        self.projection_matrix = matrix

    def set_layers_to_draw(self, layers_to_draw):
        assert 1 <= layers_to_draw <= self.layer_count, \
            f"Value of parameter layers_to_draw {layers_to_draw} not within range (1, {self.layer_count})"
        self.layers_to_draw = layers_to_draw

    def draw(self):
        if not self.initialized:
            self.init()

        with self.program:
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

            glBindVertexArray(self.vao)

            with self.index_buffer:
                glEnable(GL_CULL_FACE)
                glDrawElements(GL_TRIANGLES, self.vertices_count_at_layer[self.layers_to_draw - 1], GL_UNSIGNED_INT,
                               None)
                glDisable(GL_CULL_FACE)


class PathToMesh:
    def __init__(self, cfg):
        self.extrusion_width_external_perimeter = cfg.extrusion_width_external_perimeter
        self.extrusion_width = cfg.extrusion_width
        self.first_layer_height = cfg.first_layer_height
        self.layer_height = cfg.layer_height

    def create_mesh(self, vertices, vertex_normals, indices, path, external_perimeter, layer_no):
        path_length = len(path) - 1

        z_height = self.first_layer_height + layer_no * self.layer_height
        layer_height = self.first_layer_height if layer_no == 0 else self.layer_height
        extrusion_width = self.extrusion_width_external_perimeter if external_perimeter else self.extrusion_width

        normals = self._create_normals_from_path(path)
        # Add to every vertex a third column with value zero
        normals = numpy.append(normals, numpy.zeros((len(normals), 1), numpy.float32), axis=1)

        # Add to every vertex a third column with the layer height
        path_ = numpy.append(path, numpy.full((path_length + 1, 1), z_height, numpy.float32), axis=1)

        self._create_line_meshes(vertices[:path_length * VERTICES_PER_LINE],
                                 vertex_normals[:path_length * VERTICES_PER_LINE],
                                 indices[:path_length * INDEX_ARRAYS_PER_LINE],
                                 path_,
                                 normals,
                                 layer_height,
                                 extrusion_width)

        self._create_corner_triangles(vertices[path_length * VERTICES_PER_LINE:],
                                      vertex_normals[path_length * VERTICES_PER_LINE:],
                                      indices[path_length * INDEX_ARRAYS_PER_LINE:],
                                      path_,
                                      normals,
                                      layer_height,
                                      extrusion_width)

    def _create_line_meshes(self, vertices, vertex_normals, indices, path, normals, layer_height, extrusion_width):
        path_length = len(path) - 1

        normals2x = numpy.repeat(normals, 2, 0)
        offsets = -normals2x * extrusion_width / 2

        center_path = numpy.empty((path_length * 2, 3), numpy.float32)
        center_path[::2] = path[:-1]
        center_path[1::2] = path[1:]

        inner_path = center_path - offsets
        outer_path = center_path + offsets

        # .\
        # ..
        vertices[:path_length * 4:2] = center_path
        vertices[1:path_length * 4:2] = outer_path - [0.0, 0.0, layer_height / 2]

        # /.
        # ..
        vertices[path_length * 4:2 * path_length * 4:2] = inner_path - [0.0, 0.0, layer_height / 2]
        vertices[path_length * 4 + 1:2 * path_length * 4:2] = center_path

        # ..
        # ./
        vertices[2 * path_length * 4:3 * path_length * 4:2] = outer_path - [0.0, 0.0, layer_height / 2]
        vertices[2 * path_length * 4 + 1:3 * path_length * 4:2] = center_path - [0.0, 0.0, layer_height]

        # ..
        # \.
        vertices[3 * path_length * 4:4 * path_length * 4:2] = center_path - [0.0, 0.0, layer_height]
        vertices[3 * path_length * 4 + 1:4 * path_length * 4:2] = inner_path - [0.0, 0.0, layer_height / 2]

        vertex_normals_ = numpy.cross(vertices[1:path_length * VERTICES_PER_LINE:4] - vertices[:path_length * 16:4],
                                      vertices[2:path_length * VERTICES_PER_LINE:4] - vertices[:path_length * 16:4])
        vertex_normals_ = normalize_3d(vertex_normals_)
        vertex_normals_ = numpy.repeat(vertex_normals_, 4, 0)

        numpy.copyto(vertex_normals[:path_length * 16], vertex_normals_)

        indices_ = numpy.array([[0, 1, 2, 2, 1, 3]], numpy.uint32)
        indices_ = numpy.repeat(indices_, path_length * INDEX_ARRAYS_PER_LINE, 0)
        indices_ += numpy.arange(0, path_length * 4 * 4, 4, dtype=numpy.uint32)[:, numpy.newaxis]

        numpy.copyto(indices[:path_length * INDEX_ARRAYS_PER_LINE], indices_)

    def _create_corner_triangles(self, vertices, vertex_normals, indices, path, normals, layer_height, extrusion_width):
        path_length = len(path) - 1

        a = numpy.roll(path, -1, 0) - path  # create vectors from vertices
        b = numpy.roll(a, -1, 0)

        # determinant > 0: left turn; determinant < 0: right turn
        determinant = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        determinant = numpy.roll(determinant[:-1], 1, 0)
        determinant_abs = numpy.absolute(determinant)

        directions = numpy.divide(determinant,
                                  determinant_abs,
                                  out=numpy.zeros_like(determinant),
                                  where=(determinant_abs != 0.0))

        offsets = -normals * extrusion_width / 2

        # calculate offset positions left and right from path for triangle vertices
        c = path[:-1] + numpy.roll(offsets, 1, 0) * directions[:, None]
        d = path[:-1] + offsets * directions[:, None]

        directions_ = directions >= 0

        # switch vertices depending on turn direction
        e = numpy.where(directions_[:, None], c, d)
        f = numpy.where(directions_[:, None], d, c)

        vertices_ = numpy.empty((path_length * 6, 3), numpy.float32)

        # upper triangle
        vertices_[:path_length * 3:3] = path[:-1]
        vertices_[1:path_length * 3:3] = e - [0.0, 0.0, layer_height / 2]
        vertices_[2:path_length * 3:3] = f - [0.0, 0.0, layer_height / 2]

        # lower triangle
        vertices_[path_length * 3:path_length * 6:3] = path[:-1] - [0.0, 0.0, layer_height]
        vertices_[path_length * 3 + 1:path_length * 6:3] = f - [0.0, 0.0, layer_height / 2]
        vertices_[path_length * 3 + 2:path_length * 6:3] = e - [0.0, 0.0, layer_height / 2]

        # "end caps"
        # determine turn direction of last and first path segment
        first = path[1] - path[0]
        last = path[-1] - path[-2]
        determinant = last[0] * first[1] - last[1] * first[0]

        if determinant >= 0:
            vertices_[0] = path[0]
            vertices_[1] = path[0] - [0.0, 0.0, layer_height]
            vertices_[2] = path[0] + offsets[0] - [0.0, 0.0, layer_height / 2]

            vertices_[path_length * 3] = path[-1]
            vertices_[path_length * 3 + 1] = path[-1] + offsets[-1] - [0.0, 0.0, layer_height / 2]
            vertices_[path_length * 3 + 2] = path[-1] - [0.0, 0.0, layer_height]
        else:
            vertices_[0] = path[0]
            vertices_[1] = path[0] - offsets[0] - [0.0, 0.0, layer_height / 2]
            vertices_[2] = path[0] - [0.0, 0.0, layer_height]

            vertices_[path_length * 3] = path[-1]
            vertices_[path_length * 3 + 1] = path[-1] - [0.0, 0.0, layer_height]
            vertices_[path_length * 3 + 2] = path[-1] - offsets[-1] - [0.0, 0.0, layer_height / 2]

        numpy.copyto(vertices, vertices_)

        vertex_normals_ = numpy.cross(vertices_[1::3] - vertices_[::3], vertices_[2::3] - vertices_[::3])
        vertex_normals_ = normalize_3d(vertex_normals_)
        vertex_normals_ = numpy.repeat(vertex_normals_, 3, 0)

        numpy.copyto(vertex_normals, vertex_normals_)

        indices_ = numpy.array([[0, 1, 2, 3, 4, 5]], numpy.uint32)
        indices_ = numpy.repeat(indices_, path_length, 0)
        indices_ += numpy.arange(0, path_length * 6, 6, dtype=numpy.uint32)[:, numpy.newaxis]
        indices_ += path_length * VERTICES_PER_LINE

        numpy.copyto(indices, indices_)

    def _create_normals_from_path(self, path):
        # calculate direction vectors
        vectors = numpy.roll(path, -1, 0)[:-1] - path[:-1]

        # calculate normals of each vector
        normals = numpy.empty_like(vectors)
        normals[:, 0], normals[:, 1] = -vectors[:, 1], vectors[:, 0]

        return normalize_2d(normals)


class LinesToMesh:
    def __init__(self, cfg):
        self.extrusion_width = cfg.extrusion_width_infill
        self.first_layer_height = cfg.first_layer_height
        self.layer_height = cfg.layer_height

    def create_mesh(self, vertices, vertex_normals, indices, lines, layer_no):
        z_height = self.first_layer_height + layer_no * self.layer_height
        layer_height = self.first_layer_height if layer_no == 0 else self.layer_height

        lines_ = numpy.reshape(lines, (len(lines) * 2, 2))
        lines_length = len(lines_)

        normals = self._create_normals_from_lines(lines_)
        # Add to every vertex a third column with value zero
        normals = numpy.append(normals, numpy.zeros((len(normals), 1), numpy.float32), axis=1)

        # Add to every vertex a third column with the layer height
        lines_ = numpy.append(lines_, numpy.full((lines_length, 1), z_height, numpy.float32), axis=1)

        self._create_line_meshes(vertices[:lines_length * VERTICES_PER_LINE],
                                 vertex_normals[:lines_length * VERTICES_PER_LINE],
                                 indices[:lines_length * INDEX_ARRAYS_PER_LINE],
                                 lines_,
                                 normals,
                                 layer_height,
                                 self.extrusion_width)

    def _create_line_meshes(self, vertices, vertex_normals, indices, lines, normals, layer_height, extrusion_width):
        lines_length = len(lines)

        normals2x = numpy.repeat(normals, 2, 0)
        offsets = -normals2x * extrusion_width / 2

        center_path = lines

        inner_path = center_path - offsets
        outer_path = center_path + offsets

        # .\
        # ..
        vertices[:lines_length * 2:2] = center_path
        vertices[1:lines_length * 2:2] = outer_path - [0.0, 0.0, layer_height / 2]

        # /.
        # ..
        vertices[lines_length * 2:2 * lines_length * 2:2] = inner_path - [0.0, 0.0, layer_height / 2]
        vertices[lines_length * 2 + 1:2 * lines_length * 2:2] = center_path

        # ..
        # ./
        vertices[2 * lines_length * 2:3 * lines_length * 2:2] = outer_path - [0.0, 0.0, layer_height / 2]
        vertices[2 * lines_length * 2 + 1:3 * lines_length * 2:2] = center_path - [0.0, 0.0, layer_height]

        # ..
        # \.
        vertices[3 * lines_length * 2:4 * lines_length * 2:2] = center_path - [0.0, 0.0, layer_height]
        vertices[3 * lines_length * 2 + 1:4 * lines_length * 2:2] = inner_path - [0.0, 0.0, layer_height / 2]

        vertex_normals_ = numpy.cross(vertices[1:lines_length * VERTICES_PER_LINE:4] - vertices[:lines_length * 16:4],
                                      vertices[2:lines_length * VERTICES_PER_LINE:4] - vertices[:lines_length * 16:4])
        vertex_normals_ = normalize_3d(vertex_normals_)
        vertex_normals_ = numpy.repeat(vertex_normals_, 4, 0)

        numpy.copyto(vertex_normals[:lines_length * 16], vertex_normals_)

        indices_ = numpy.array([[0, 1, 2, 2, 1, 3]], numpy.uint32)
        indices_ = numpy.repeat(indices_, lines_length * INDEX_ARRAYS_PER_LINE, 0)
        indices_ += numpy.arange(0, lines_length * 4 * 4, 4, dtype=numpy.uint32)[:, numpy.newaxis]

        numpy.copyto(indices[:lines_length * INDEX_ARRAYS_PER_LINE], indices_)

    def _create_normals_from_lines(self, lines):
        # calculate direction vectors
        vectors = lines[1::2] - lines[::2]

        # calculate normals of each vector
        normals = numpy.empty_like(vectors)
        normals[:, 0], normals[:, 1] = -vectors[:, 1], vectors[:, 0]

        return normalize_2d(normals)


def normalize_2d(a):
    """
    Normalizes each 2D vector in given array
    :param a: numpy.array() of 2D vectors
    :return: numpy.array() of 2D vectors
    """
    return a / numpy.sqrt((a[:, 0] ** 2) + a[:, 1] ** 2)[:, numpy.newaxis]


def normalize_3d(a):
    """
    Normalizes each 3D vector in given array
    :param a: numpy.array() of 3D vectors
    :return: numpy.array() of 3D vectors
    """
    b = numpy.sqrt((a[:, 0] ** 2) + a[:, 1] ** 2 + a[:, 2] ** 2)[:, numpy.newaxis]
    return numpy.divide(a, b, out=numpy.zeros_like(a), where=(b != 0))
