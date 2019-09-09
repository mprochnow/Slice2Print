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
import wx

from glhelpers import GlBuffer, rotate_x, ShaderProgram
import glmesh
import glview

# numpy.seterr(all="raise")


class LayerView(wx.Panel):
    def __init__(self, parent, build_volume):
        wx.Panel.__init__(self, parent)

        self.gl_canvas = glview.GlCanvas(self)
        self.slider = wx.Slider(self, wx.ID_ANY, 1, 1, 2, style=wx.SL_INVERSE | wx.SL_LEFT | wx.SL_VERTICAL)
        self.layer_label = wx.StaticText(self, wx.ID_ANY, "1", style=wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL)

        slider_sizer = wx.BoxSizer(wx.VERTICAL)
        slider_sizer.Add(wx.StaticText(self, wx.ID_ANY, "Layer:"), 0, wx.ALIGN_CENTER_HORIZONTAL)
        slider_sizer.Add(self.layer_label, 0, wx.ALIGN_CENTER_HORIZONTAL)
        slider_sizer.Add(self.slider, 1, wx.ALIGN_CENTER_HORIZONTAL)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.gl_canvas, 1, wx.EXPAND)
        sizer.Add(slider_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 7)
        self.SetSizer(sizer)
        self.Layout()

        self.Bind(wx.EVT_SLIDER, self.on_slider, id=self.slider.GetId())

        self.slider.Enable(False)
        self.gl_canvas.set_platform_mesh(glmesh.PlatformMesh(build_volume))

    def set_sliced_model(self, sliced_model):
        self.set_layer_count(sliced_model.layer_count)

        mesh = LayerMesh(sliced_model)

        self.gl_canvas.set_model_mesh(mesh)
        self.view_all()

    def view_all(self):
        self.gl_canvas.view_all()

    def set_layer_count(self, layer_count):
        self.slider.SetRange(1, layer_count)
        self.slider.SetValue(layer_count)
        self.slider.Enable(True)

        self.layer_label.SetLabelText(str(layer_count))

        self.Layout()

    def on_slider(self, event):
        layer = event.GetInt()

        self.layer_label.SetLabelText(str(layer))
        self.Layout()

        self.gl_canvas.model_mesh.set_layers_to_draw(layer)
        self.gl_canvas.Refresh()


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
        # Arrays will be created with needed size, this avoid expensive allocation and copy operations
        vertices = numpy.zeros((self.sliced_model.node_count * VERTICES_PER_NODE, 3), numpy.float32)
        normals = numpy.zeros((self.sliced_model.node_count * NORMALS_PER_NODE, 3), numpy.float32)
        indices = numpy.zeros((self.sliced_model.node_count * INDEX_ARRAYS_PER_NODE, 6), numpy.uint32)

        p2m = PathToMesh(self.sliced_model.cfg)

        node_count = 0
        for layer in self.sliced_model.layers:
            for perimeter in layer.perimeters:
                for path in perimeter:
                    path_length = len(path)

                    v = vertices[node_count * VERTICES_PER_NODE:(node_count + path_length) * VERTICES_PER_NODE]
                    n = normals[node_count * NORMALS_PER_NODE:(node_count + path_length) * NORMALS_PER_NODE]
                    i = indices[node_count * INDEX_ARRAYS_PER_NODE:(node_count + path_length) * INDEX_ARRAYS_PER_NODE]

                    p2m.create_mesh(v, n, i, path, layer.z)

                    i += node_count * VERTICES_PER_NODE

                    node_count += path_length

            self.vertices_count_at_layer.append(node_count * INDEX_ARRAYS_PER_NODE * 6)

        return vertices.ravel() / self.sliced_model.cfg.VERTEX_PRECISION, normals.ravel(), indices.ravel()

    def delete(self):
        self.vertex_buffer.delete()
        glDeleteVertexArrays(1, [self.vao])

    def update_view_matrix(self, matrix):
        self.view_matrix = matrix

    def update_projection_matrix(self, matrix):
        self.projection_matrix = matrix

    def set_layers_to_draw(self, layers_to_draw):
        assert 1 <= layers_to_draw <= self.layer_count, "Value of parameter layers_to_draw not within range"
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
        self.extrusion_width = cfg.extrusion_width * cfg.VERTEX_PRECISION
        self.layer_height = cfg.layer_height * cfg.VERTEX_PRECISION

    def create_mesh(self, vertices, vertex_normals, indices, path, z_height):
        path_length = len(path)

        normals = self._create_normals_from_path(path)
        normals = numpy.append(normals,
                               numpy.zeros((len(normals), 1), numpy.float32),
                               axis=1)
        normals2x = numpy.repeat(normals, 2, 0)
        offsets = -normals2x * self.extrusion_width / 2

        # Add to every vertex a third column with the layer height
        path = numpy.append(path,
                            numpy.full((path_length, 1), z_height, numpy.float32),
                            axis=1)

        center_path = numpy.empty((path_length * 2, 3), numpy.float32)
        center_path[::2] = path
        center_path[1::2] = numpy.roll(path, -1, 0)

        inner_path = center_path - offsets
        outer_path = center_path + offsets

        # .\
        # ..
        vertices[:path_length * 4:2] = center_path
        vertices[1:path_length * 4:2] = outer_path - [0.0, 0.0, self.layer_height / 2]

        # /.
        # ..
        vertices[path_length * 4:2 * path_length * 4:2] = inner_path - [0.0, 0.0, self.layer_height / 2]
        vertices[path_length * 4 + 1:2 * path_length * 4:2] = center_path

        # ..
        # ./
        vertices[2 * path_length * 4:3 * path_length * 4:2] = outer_path - [0.0, 0.0, self.layer_height / 2]
        vertices[2 * path_length * 4 + 1:3 * path_length * 4:2] = center_path - [0.0, 0.0, self.layer_height]

        # ..
        # \.
        vertices[3 * path_length * 4:4 * path_length * 4:2] = center_path - [0.0, 0.0, self.layer_height]
        vertices[3 * path_length * 4 + 1:4 * path_length * 4:2] = inner_path - [0.0, 0.0, self.layer_height / 2]

        vertex_normals_ = numpy.cross(vertices[1:path_length * VERTICES_PER_LINE:4] - vertices[:path_length * 16:4],
                                      vertices[2:path_length * VERTICES_PER_LINE:4] - vertices[:path_length * 16:4])
        vertex_normals_ = self._normalize_3d(vertex_normals_)
        vertex_normals_ = numpy.repeat(vertex_normals_, 4, 0)

        numpy.copyto(vertex_normals[:path_length * 16], vertex_normals_)

        indices_ = numpy.array([[0, 1, 2, 2, 1, 3],
                                [0, 1, 2, 2, 1, 3],
                                [0, 1, 2, 2, 1, 3],
                                [0, 1, 2, 2, 1, 3]], numpy.uint32)

        indices_ = numpy.repeat(indices_, path_length, 0)
        indices_ += numpy.arange(0, path_length * 4 * 4, 4, dtype=numpy.uint32)[:, numpy.newaxis]

        numpy.copyto(indices[:path_length * INDEX_ARRAYS_PER_LINE], indices_)

        self._create_corner_triangles(vertices[path_length * VERTICES_PER_LINE:],
                                      vertex_normals[path_length * VERTICES_PER_LINE:],
                                      indices[path_length * INDEX_ARRAYS_PER_LINE:],
                                      path,
                                      normals, )

    def _create_corner_triangles(self, vertices, vertex_normals, indices, path, normals):
        path_length = len(path)

        a = numpy.roll(path, -1, 0) - path
        b = numpy.roll(a, -1, 0)

        # determinant > 0: left turn; determinant < 0: right turn
        determinant = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
        determinant = numpy.roll(determinant, 1, 0)
        determinant_abs = numpy.absolute(determinant)
        directions = numpy.divide(determinant, determinant_abs, where=(determinant_abs != 0))

        offsets = -normals * self.extrusion_width / 2

        c = path + numpy.roll(offsets, 1, 0) * directions[:, None]
        d = path + offsets * directions[:, None]

        directions_ = directions >= 0

        e = numpy.where(directions_[:, None], c, d)
        f = numpy.where(directions_[:, None], d, c)

        vertices_ = numpy.empty((path_length * 6, 3), numpy.float32)

        # upper triangle
        vertices_[:path_length * 3:3] = path
        vertices_[1:path_length * 3:3] = e - [0.0, 0.0, self.layer_height / 2]
        vertices_[2:path_length * 3:3] = f - [0.0, 0.0, self.layer_height / 2]

        # lower triangle
        vertices_[path_length * 3:path_length * 6:3] = path - [0.0, 0.0, self.layer_height]
        vertices_[path_length * 3 + 1:path_length * 6:3] = f - [0.0, 0.0, self.layer_height / 2]
        vertices_[path_length * 3 + 2:path_length * 6:3] = e - [0.0, 0.0, self.layer_height / 2]

        numpy.copyto(vertices, vertices_)

        vertex_normals_ = numpy.cross(vertices_[1::3] - vertices_[::3], vertices_[2::3] - vertices_[::3])
        vertex_normals_ = self._normalize_3d(vertex_normals_)
        vertex_normals_ = numpy.repeat(vertex_normals_, 3, 0)

        numpy.copyto(vertex_normals, vertex_normals_)

        indices_ = numpy.array([[0, 1, 2, 3, 4, 5]], numpy.uint32)
        indices_ = numpy.repeat(indices_, path_length, 0)
        indices_ += numpy.arange(0, path_length * 6, 6, dtype=numpy.uint32)[:, numpy.newaxis]
        indices_ += path_length * VERTICES_PER_LINE

        numpy.copyto(indices, indices_)

    def _create_normals_from_path(self, path):
        # calculate direction vectors
        vectors = numpy.roll(path, -1, 0) - path

        # calculate normals of each vector
        normals = numpy.empty(vectors.shape, numpy.float32)
        normals[:, 0], normals[:, 1] = -vectors[:, 1], vectors[:, 0]

        return self._normalize_2d(normals)

    @staticmethod
    def _normalize_2d(a):
        return a / numpy.sqrt((a[:, 0] ** 2) + a[:, 1] ** 2)[:, numpy.newaxis]

    @staticmethod
    def _normalize_3d(a):
        b = numpy.sqrt((a[:, 0] ** 2) + a[:, 1] ** 2 + a[:, 2] ** 2)[:, numpy.newaxis]
        return numpy.divide(a, b, where=(b != 0))
