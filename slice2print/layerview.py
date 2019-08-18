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

        mesh = LayerMesh.from_sliced_model(sliced_model)

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
    def __init__(self, vertices, bounding_box, layer_count, vertices_count_at_layer):
        self.initialized = False
        self.vertices = vertices
        self.bounding_box = bounding_box
        self.layer_count = layer_count
        self.vertices_count_at_layer = vertices_count_at_layer
        self.layers_to_draw = layer_count

        self.program = None
        self.buffer = None
        self.vao = None

        self.model_color = numpy.array([0.0, 0.0, 0.0, 1.0], numpy.float32)
        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)

        # OpenGL z-axis points in a different direction, so we have to flip the model
        self.model_matrix = rotate_x(-90)

    @classmethod
    def from_sliced_model(cls, sliced_model):
        vertices_count_at_layer = []
        vertices_count = 0

        for layer in sliced_model.layers:
            for perimeter in layer.perimeters:
                for path in perimeter:
                    vertices_count += len(path) * 2

            vertices_count_at_layer.append(vertices_count)

        vertices = numpy.zeros([vertices_count, 3], dtype=numpy.float32)

        i = 0
        for layer in sliced_model.layers:
            for perimeter in layer.perimeters:
                for path in perimeter:
                    first = last = p1 = p2 = None

                    for point in path:
                        x = point[0] / sliced_model.cfg.VERTEX_PRECISION
                        y = point[1] / sliced_model.cfg.VERTEX_PRECISION
                        z = layer.z

                        if p1 is None:
                            p1 = (x, y, z)
                            first = p1
                        elif p2 is None:
                            p2 = (x, y, z)
                        else:
                            p1 = p2
                            p2 = (x, y, z)
                            last = p2

                        if p1 is not None and p2 is not None:
                            vertices[i] = p1
                            vertices[i+1] = p2
                            i += 2

                    # close the loop
                    vertices[i] = first
                    vertices[i+1] = last
                    i += 2

        vertices = numpy.array(vertices, numpy.float32).flatten()

        return cls(vertices, sliced_model.bounding_box, sliced_model.layer_count, vertices_count_at_layer)

    def init(self):
        self.initialized = True

        self.program = ShaderProgram(glmesh.BASIC_VERTEX_SHADER, glmesh.BASIC_FRAGMENT_SHADER)
        self.buffer = GlBuffer(self.vertices, GL_ARRAY_BUFFER)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vertex_position_index = self.program.get_attrib_location("vertex_position")

        with self.buffer:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

        with self.program:
            self.program.model_color = self.model_color
            self.program.model_matrix = self.model_matrix
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

    def delete(self):
        self.buffer.delete()
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

            with self.buffer:
                glDrawArrays(GL_LINES, 0, self.vertices_count_at_layer[self.layers_to_draw - 1])
