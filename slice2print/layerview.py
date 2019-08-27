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
import numpy
import wx

from glhelpers import GlBuffer, rotate_x, ShaderProgram
import glmesh
import glview


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


class LayerMesh:
    def __init__(self, sliced_model):
        self.initialized = False
        self.program = None
        self.vertex_buffer = None
        self.vao = None

        self.sliced_model = sliced_model
        self.bounding_box = sliced_model.bounding_box
        self.layer_count = sliced_model.layer_count
        self.layers_to_draw = sliced_model.layer_count

        self.vertices_count_at_layer = []

        self.model_color = numpy.array([0.0, 0.0, 0.0, 1.0], numpy.float32)
        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)

        # OpenGL z-axis points in a different direction, so we have to flip the model
        self.model_matrix = rotate_x(-90)

    def init(self):
        self.initialized = True

        vertices = self.create_mesh(self.sliced_model)

        self.program = ShaderProgram(glmesh.BASIC_VERTEX_SHADER, glmesh.BASIC_FRAGMENT_SHADER)
        self.vertex_buffer = GlBuffer(vertices, GL_ARRAY_BUFFER)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vertex_position_index = self.program.get_attrib_location("vertex_position")

        with self.vertex_buffer:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

        with self.program:
            self.program.model_color = self.model_color
            self.program.model_matrix = self.model_matrix
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

    def create_mesh(self, sliced_model):
        vertices = numpy.zeros((0, 3), dtype=numpy.float32)

        i = 0
        for layer in sliced_model.layers:
            for perimeter in layer.perimeters:
                for path in perimeter:
                    # Add to every entry of path a third column with layer height
                    a = numpy.append(path,
                                     numpy.full((len(path), 1), layer.z, vertices.dtype),
                                     axis=1)

                    # Resize array to contain new elements
                    vertices.resize(i+len(path)*2, 3)

                    # Interweave points of path to create lines and close loop
                    # e.g. (p1, p2, p3) => ((p1, p2), (p2, p3), (p3, p1))
                    vertices[i::2] = a
                    vertices[i+1::2] = numpy.concatenate([a[1:], a[:1]])

                    i += len(path)*2

            self.vertices_count_at_layer.append(i)

        return vertices.ravel() / sliced_model.cfg.VERTEX_PRECISION

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

            with self.vertex_buffer:
                glDrawArrays(GL_LINES, 0, self.vertices_count_at_layer[self.layers_to_draw - 1])


class PathToMesh:
    def __init__(self, path, extrusion_width, z_height):
        self.path = path
        self.extrusion_width = extrusion_width
        self.z_height = z_height

    def create_mesh(self):
        vertices = self._create_vertices()
        normals = self._create_vertex_normals()
        indices = self._create_indices()

        return vertices, normals, indices

    def _create_vertices(self):
        normals = self._create_normals_from_path()
        bisectors = self._create_bisectors_from_normals(normals)
        bisector_cosines = self._create_bisector_cosines_from_normals(normals)

        lengths = 0.5*self.extrusion_width / bisector_cosines

        bisectors *= lengths[:, numpy.newaxis]

        inner_path = self.path + bisectors
        inner_path = numpy.repeat(inner_path, 2, 0)
        inner_path = numpy.roll(inner_path, -1, 0)

        outer_path = self.path - bisectors
        outer_path = numpy.repeat(outer_path, 2, 0)
        outer_path = numpy.roll(outer_path, -1, 0)

        vertices = numpy.empty((len(inner_path)+len(outer_path), 2), numpy.float32)
        vertices[::2] = inner_path
        vertices[1::2] = outer_path

        # Add to every vertex a third column with the layer height
        vertices = numpy.append(vertices,
                                numpy.full((len(vertices), 1), self.z_height, vertices.dtype),
                                axis=1)

        return vertices

    def _create_vertex_normals(self):
        return numpy.repeat(numpy.array([[0.0, 0.0, 1.0]], numpy.float32), len(self.path) * 4, 0)


    def _create_indices(self):
        indices = numpy.array([[0, 1, 2, 2, 1, 3]], numpy.uint32)
        indices = numpy.repeat(indices, len(self.path), 0)
        indices += numpy.arange(0, len(self.path) * 4, 4, dtype=numpy.uint32)[:, numpy.newaxis]

        return indices

    def _create_normals_from_path(self):
        # calculate direction vectors
        vectors = numpy.roll(self.path, -1, 0) - self.path

        # calculate normals of each vector
        normals = numpy.empty(vectors.shape, numpy.float32)
        normals[:, 0], normals[:, 1] = -vectors[:, 1], vectors[:, 0]

        return self._normalize(normals)

    def _create_bisectors_from_normals(self, normals):
        bisectors = numpy.roll(normals, 1, 0) + normals

        return self._normalize(bisectors)

    def _create_bisector_cosines_from_normals(self, normals):
        dot_products = self._dot_product(numpy.roll(normals, 1, 0), normals)
        # Half-angle formula: cos(x)/2 = sqrt((1+cos(x))/2)
        return numpy.sqrt((1 + dot_products)/2)

    @staticmethod
    def _normalize(a):
        return a / numpy.sqrt((a[:, 0]**2) + a[:, 1]**2)[:, numpy.newaxis]

    @staticmethod
    def _dot_product(a, b):
        return numpy.sum(a * b, axis=1)


if __name__ == "__main__":
    extrusion_width = 2.0
    z_height = 1.0
    path = numpy.array([[-10, -10],
                        [10, -10],
                        [10, 10],
                        [-10, 10]])

    p2m = PathToMesh(path, extrusion_width, z_height)
    vertices, normals, indices = p2m.create_mesh()

    print(vertices)
    print(normals)
    print(indices)
