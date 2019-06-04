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


MODEL_VERTEX_SHADER = """
    #version 150

    in vec3 vertex_normal;
    in vec3 vertex_position;

    uniform mat4 model_matrix;
    uniform mat4 view_matrix;
    uniform mat4 projection_matrix;

    out vec3 color;

    vec3 light_position = vec3 (1.0, 1.0, -1.0);

    void main() {
        gl_Position = projection_matrix * view_matrix * model_matrix * vec4(vertex_position, 1.0);

        vec3 normal_eye = vec3(transpose(inverse(view_matrix * model_matrix)) * vec4(vertex_normal, 0.0));

        float light = 0.2 + abs(dot(normalize(normal_eye), normalize(light_position)));

        color = vec3(1.0, 0.5, 0.0) * light;
    }
    """

MODEL_FRAGMENT_SHADER = """
    #version 150

    in vec3 color;
    out vec4 frag_colour;

    void main() {
        frag_colour = vec4(color, 1.0);
    }
    """


class ModelMesh:
    def __init__(self, vertices, normals, indices, bounding_box):
        """
        :param vertices: numpy.array() containing the vertices
        :param normals: numpy.array() containing the normals
        :param indices:  numpy.array() containing the indices
        :param bounding_box:  Instance of model.BoundingBox
        """
        self.program = ShaderProgram(MODEL_VERTEX_SHADER, MODEL_FRAGMENT_SHADER)

        self.model_matrix = numpy.identity(4, numpy.float32)
        self.model_matrix[3][0] = -(bounding_box.x_max+bounding_box.x_min) / 2
        self.model_matrix[3][1] = -(bounding_box.y_max+bounding_box.y_min) / 2
        self.model_matrix[3][2] = -bounding_box.z_min

        # OpenGL z-axis points in a different direction, so we have to flip the model
        self.model_matrix = numpy.dot(self.model_matrix, rotate_x(-90))

        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)

        self.model_matrix_location = self.program.get_uniform_location("model_matrix")
        self.view_matrix_location = self.program.get_uniform_location("view_matrix")
        self.projection_matrix_location = self.program.get_uniform_location("projection_matrix")

        vertex_position_index = self.program.get_attrib_location("vertex_position")
        vertex_normal_index = self.program.get_attrib_location("vertex_normal")

        self.vertices = GlBuffer(vertices, GL_ARRAY_BUFFER)
        self.normals = GlBuffer(normals, GL_ARRAY_BUFFER)
        self.indices = GlBuffer(indices, GL_ELEMENT_ARRAY_BUFFER)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        with self.vertices:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

        with self.normals:
            glVertexAttribPointer(vertex_normal_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_normal_index)

        with self.program:
            glUniformMatrix4fv(self.model_matrix_location, 1, GL_FALSE, self.model_matrix)
            glUniformMatrix4fv(self.view_matrix_location, 1, GL_FALSE, self.view_matrix)
            glUniformMatrix4fv(self.projection_matrix_location, 1, GL_FALSE, self.projection_matrix)

    def __del__(self):
        glDeleteVertexArrays(1, [self.vao])

    def update_mesh(self, vertices, normals, indices, bounding_box):
        """
        :param vertices: numpy.array() containing the vertices
        :param normals: numpy.array() containing the normals
        :param indices:  numpy.array() containing the indices
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
            glUniformMatrix4fv(self.view_matrix_location, 1, GL_FALSE, self.view_matrix)
            glUniformMatrix4fv(self.projection_matrix_location, 1, GL_FALSE, self.projection_matrix)

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

PLATFORM_LINE_VERTEX_SHADER = """
    #version 150

    in vec3 vertex_position;

    uniform mat4 view_matrix;
    uniform mat4 projection_matrix;

    void main() {
        gl_Position = projection_matrix * view_matrix * vec4(vertex_position, 1.0);
    }
"""

PLATFORM_LINE_FRAGMENT_SHADER = """
    #version 150

    out vec4 frag_colour;

    void main() {
        frag_colour = vec4(0.0, 0.0, 0.0, 0.1);
    }
"""


class PlatformMesh:
    """
    Renders the build volume. Shows a checker board pattern at the bottom and
    back plane. Additionally, edges of build volume a drawn as lines.
    """
    def __init__(self, dimensions):
        """
        :param dimensions: Dimensions of build volume as tuple (x, y, z)
        """
        self.initialized = False
        self.dimensions = dimensions
        self.triangle_program = None
        self.line_program = None

        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)
        self.vertices = None
        self.triangle_indices = None
        self.line_indices = None
        self.vao = None

    def __del__(self):
        glDeleteVertexArrays(1, [self.vao])

    def init(self):
        self.initialized = True

        self.triangle_program = ShaderProgram(PLATFORM_VERTEX_SHADER, PLATFORM_FRAGMENT_SHADER)
        self.line_program = ShaderProgram(PLATFORM_LINE_VERTEX_SHADER, PLATFORM_LINE_FRAGMENT_SHADER)

        vertex_position_index = self.triangle_program.get_attrib_location("vertex_position")

        self.vertices = GlBuffer()
        self.triangle_indices = GlBuffer()
        self.line_indices = GlBuffer()

        self.set_dimensions(self.dimensions)

        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)

        with self.vertices:
            glVertexAttribPointer(vertex_position_index, 3, GL_FLOAT, GL_FALSE, 0, None)
            glEnableVertexAttribArray(vertex_position_index)

    def update_view_matrix(self, matrix):
        self.view_matrix = matrix

    def update_projection_matrix(self, matrix):
        self.projection_matrix = matrix

    def draw(self):
        if not self.initialized:
            self.init()

        with self.triangle_program:
            glUniformMatrix4fv(self.triangle_program.get_uniform_location("view_matrix"),
                               1, GL_FALSE, self.view_matrix)
            glUniformMatrix4fv(self.triangle_program.get_uniform_location("projection_matrix"),
                               1, GL_FALSE, self.projection_matrix)

            glBindVertexArray(self.vao)

            with self.triangle_indices:
                # Offset polygon rendering so that no flickering occurs when model is displayed on build platform
                glPolygonOffset(-1.0, -1.0)
                glEnable(GL_POLYGON_OFFSET_FILL)

                glDrawElements(GL_TRIANGLES, len(self.triangle_indices), GL_UNSIGNED_INT, None)

                glDisable(GL_POLYGON_OFFSET_FILL)

        with self.line_program:
            glUniformMatrix4fv(self.line_program.get_uniform_location("view_matrix"),
                               1, GL_FALSE, self.view_matrix)
            glUniformMatrix4fv(self.line_program.get_uniform_location("projection_matrix"),
                               1, GL_FALSE, self.projection_matrix)

            glBindVertexArray(self.vao)

            with self.line_indices:
                glDrawElements(GL_LINES, len(self.line_indices), GL_UNSIGNED_INT, None)

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

        line_indices = numpy.array([0, 1,
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
        self.triangle_indices.set_data(triangle_indices, GL_ELEMENT_ARRAY_BUFFER)
        self.line_indices.set_data(line_indices, GL_ELEMENT_ARRAY_BUFFER)
