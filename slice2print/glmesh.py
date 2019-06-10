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

from glhelpers import *


BASIC_VERTEX_SHADER = """
    #version 150

    in vec3 vertex_position;

    uniform vec4 model_color;
    uniform mat4 model_matrix;
    uniform mat4 view_matrix;
    uniform mat4 projection_matrix;

    out vec4 color;

    void main() {
        gl_Position = projection_matrix * view_matrix * model_matrix * vec4(vertex_position, 1.0);
        color = model_color;
    }
"""

BASIC_FRAGMENT_SHADER = """
    #version 150

    in vec4 color;
    out vec4 frag_colour;

    void main() {
        frag_colour = color;
    }
"""


MODEL_VERTEX_SHADER = """
    #version 150

    in vec3 vertex_normal;
    in vec3 vertex_position;

    uniform vec4 model_color;
    uniform mat4 model_matrix;
    uniform mat4 view_matrix;
    uniform mat4 projection_matrix;

    out vec4 color;

    vec3 light_position = vec3 (1.0, 1.0, -1.0);

    void main() {
        gl_Position = projection_matrix * view_matrix * model_matrix * vec4(vertex_position, 1.0);

        vec3 normal_eye = vec3(transpose(inverse(view_matrix * model_matrix)) * vec4(vertex_normal, 0.0));

        float light = 0.2 + abs(dot(normalize(normal_eye), normalize(light_position)));

        color = vec4(model_color[0] * light,
                     model_color[1] * light,
                     model_color[2] * light,
                     model_color[3]);
    }
"""


class ModelMesh:
    def __init__(self, vertices, normals, indices, bounding_box):
        """
        :param vertices: numpy.array() containing the vertices
        :param normals: numpy.array() containing the normals
        :param indices: numpy.array() containing the indices
        :param bounding_box:  Instance of model.BoundingBox
        """
        self.program = ShaderProgram(MODEL_VERTEX_SHADER, BASIC_FRAGMENT_SHADER)
        self.bounding_box = bounding_box

        self.model_color = numpy.array([1.0, 0.5, 0.0, 1.0], numpy.float32)

        self.model_matrix = numpy.identity(4, numpy.float32)
        self.model_matrix[3][0] = -(bounding_box.x_max+bounding_box.x_min) / 2
        self.model_matrix[3][1] = -(bounding_box.y_max+bounding_box.y_min) / 2
        self.model_matrix[3][2] = -bounding_box.z_min

        # OpenGL z-axis points in a different direction, so we have to flip the model
        self.model_matrix = numpy.matmul(self.model_matrix, rotate_x(-90))

        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)

        self.vertices = GlBuffer(vertices, GL_ARRAY_BUFFER)
        self.normals = GlBuffer(normals, GL_ARRAY_BUFFER)
        self.indices = GlBuffer(indices, GL_ELEMENT_ARRAY_BUFFER)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vertex_position_index = self.program.get_attrib_location("vertex_position")
        vertex_normal_index = self.program.get_attrib_location("vertex_normal")

        with self.vertices:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

        with self.normals:
            glVertexAttribPointer(vertex_normal_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_normal_index)

        with self.program:
            self.program.model_color = self.model_color
            self.program.model_matrix = self.model_matrix
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

    def delete(self):
        self.vertices.delete()
        self.normals.delete()
        self.indices.delete()
        glDeleteVertexArrays(1, [self.vao])

    def update_mesh(self, vertices, normals, indices, bounding_box):
        """
        :param vertices: numpy.array() containing the vertices
        :param normals: numpy.array() containing the normals
        :param indices: numpy.array() containing the indices
        :param bounding_box:  Instance of model.BoundingBox
        """
        self.vertices.set_data(vertices, GL_ARRAY_BUFFER)
        self.normals.set_data(normals, GL_ARRAY_BUFFER)
        self.indices.set_data(indices, GL_ELEMENT_ARRAY_BUFFER)

        self.model_matrix[3][0] = -(bounding_box.x_max+bounding_box.x_min) / 2
        self.model_matrix[3][1] = -(bounding_box.y_max+bounding_box.y_min) / 2
        self.model_matrix[3][2] = -bounding_box.z_min

    def update_view_matrix(self, matrix):
        self.view_matrix = matrix

    def update_projection_matrix(self, matrix):
        self.projection_matrix = matrix

    def draw(self):
        with self.program:
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

            glBindVertexArray(self.vao)

            with self.indices:
                glDrawElements(GL_TRIANGLES, len(self.indices), GL_UNSIGNED_INT, None)


PLATFORM_VERTEX_SHADER = """
    #version 150

    in vec3 vertex_position;

    uniform mat4 view_matrix;
    uniform mat4 projection_matrix;

    out vec3 pos;

    void main() {
        gl_Position = projection_matrix * view_matrix * vec4(vertex_position, 1.0);
        pos = vertex_position;
    }
"""

PLATFORM_FRAGMENT_SHADER = """
    #version 150

    in vec3 pos;
    out vec4 frag_colour;

    void main() {
        vec3 pos_scaled = pos / 10.0;

        // https://www.ronja-tutorials.com/2018/05/18/Chessboard.html#checkerboard-in-2d-and-3d        
        float color = (int(floor(pos_scaled.x) + floor(pos_scaled.y) + floor(pos_scaled.z)) & 1) * 2.0;

        frag_colour = vec4(color, color, color, 0.1);
    }
"""


class PlatformMesh:
    """
    Renders the build volume. Shows a checker board pattern at the bottom and
    back plane. Additionally, edges of build volume are drawn as lines.
    """
    def __init__(self, dimensions):
        """
        :param dimensions: Dimensions of build volume as tuple (x, y, z)
        """
        self.initialized = False
        self.dimensions = dimensions
        self.triangle_program = None
        self.line_program = None

        self.line_color = numpy.array([0.0, 0.0, 0.0, 0.1], numpy.float32)

        self.model_matrix = numpy.identity(4, numpy.float32)
        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)
        self.vertices = None
        self.plane_indices = None
        self.outline_indices = None
        self.vao = None

    def init(self):
        self.initialized = True

        self.triangle_program = ShaderProgram(PLATFORM_VERTEX_SHADER, PLATFORM_FRAGMENT_SHADER)
        self.line_program = ShaderProgram(BASIC_VERTEX_SHADER, BASIC_FRAGMENT_SHADER)

        self.vertices = GlBuffer()
        self.plane_indices = GlBuffer()
        self.outline_indices = GlBuffer()

        self.set_dimensions(self.dimensions)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        vertex_position_index = self.triangle_program.get_attrib_location("vertex_position")

        with self.vertices:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

        with self.line_program:
            self.line_program.model_color = self.line_color
            self.line_program.model_matrix = self.model_matrix

    def update_view_matrix(self, matrix):
        self.view_matrix = matrix

    def update_projection_matrix(self, matrix):
        self.projection_matrix = matrix

    def draw(self):
        if not self.initialized:
            self.init()

        with self.triangle_program:
            self.triangle_program.view_matrix = self.view_matrix
            self.triangle_program.projection_matrix = self.projection_matrix

            glBindVertexArray(self.vao)

            with self.plane_indices:
                # Offset polygon rendering so that no flickering occurs when model is displayed on build platform
                glPolygonOffset(-1.0, -1.0)
                glEnable(GL_POLYGON_OFFSET_FILL)

                glDrawElements(GL_TRIANGLES, len(self.plane_indices), GL_UNSIGNED_INT, None)

                glDisable(GL_POLYGON_OFFSET_FILL)

        with self.line_program:
            self.line_program.view_matrix = self.view_matrix
            self.line_program.projection_matrix = self.projection_matrix

            glBindVertexArray(self.vao)

            with self.outline_indices:
                glDrawElements(GL_LINES, len(self.outline_indices), GL_UNSIGNED_INT, None)

    def set_dimensions(self, dimensions):
        """
        :param dimensions: Dimensions of build volume as tuple (x, y, z)
        """
        x = dimensions[0]
        y = dimensions[2]  # y is pointing upwards in OpenGL
        z = dimensions[1]  # z is pointing "out of the screen" in OpenGL

        vertices = numpy.array([[-x/2, 0, z/2],
                                [x/2, 0, z/2],
                                [x/2, 0, -z/2],
                                [-x/2, 0, -z/2],
                                [x/2, y, -z/2],
                                [-x/2, y, -z/2],
                                [-x/2, y, z/2],
                                [x/2, y, z/2]], numpy.float32)

        triangle_indices = numpy.array([0, 1, 2,
                                        2, 3, 0,
                                        3, 2, 4,
                                        3, 4, 5], numpy.uint32)

        outline_indices = numpy.array([0, 1,
                                       0, 6,
                                       1, 2,
                                       1, 7,
                                       2, 3,
                                       2, 4,
                                       3, 0,
                                       3, 5,
                                       4, 5,
                                       4, 7,
                                       5, 6,
                                       6, 7], numpy.uint32)

        self.vertices.set_data(vertices, GL_ARRAY_BUFFER)
        self.plane_indices.set_data(triangle_indices, GL_ELEMENT_ARRAY_BUFFER)
        self.outline_indices.set_data(outline_indices, GL_ELEMENT_ARRAY_BUFFER)


class LayerMesh:
    def __init__(self, vertices, bounding_box):
        self.initialized = False
        self.vertices = vertices
        self.bounding_box = bounding_box

        self.program = None
        self.buffer = None
        self.vao = None

        self.model_color = numpy.array([0.0, 0.0, 0.0, 1.0], numpy.float32)
        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)

        self.model_matrix = numpy.identity(4, numpy.float32)
        self.model_matrix[3][0] = -(bounding_box.x_max+bounding_box.x_min) / 2
        self.model_matrix[3][1] = -(bounding_box.y_max+bounding_box.y_min) / 2
        self.model_matrix[3][2] = -bounding_box.z_min

        # OpenGL z-axis points in a different direction, so we have to flip the model
        self.model_matrix = numpy.matmul(self.model_matrix, rotate_x(-90))

    def init(self):
        self.initialized = True

        self.program = ShaderProgram(BASIC_VERTEX_SHADER, BASIC_FRAGMENT_SHADER)
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

    def draw(self):
        if not self.initialized:
            self.init()

        with self.program:
            self.program.view_matrix = self.view_matrix
            self.program.projection_matrix = self.projection_matrix

            glBindVertexArray(self.vao)

            with self.buffer:
                glDrawArrays(GL_LINES, 0, len(self.buffer))
