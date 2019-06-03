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

    vec3 light_position = vec3 (-1.0, 1.0, 1.0);

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

        self.vertices = GlBuffer(vertices)
        self.normals = GlBuffer(normals)
        self.indices = GlBuffer(indices, numpy.uint32, GL_ELEMENT_ARRAY_BUFFER)

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


class PlatformMesh:
    def __init__(self, dimensions):
        self.initialized = False
        self.dimensions = dimensions
        self.program = None

        self.view_matrix = numpy.identity(4, numpy.float32)
        self.projection_matrix = numpy.identity(4, numpy.float32)
        self.view_matrix_location = None
        self.projection_matrix_location = None
        self.vertices = None
        self.vao = None

    def init(self):
        self.initialized = True

        self.program = ShaderProgram("""
        #version 150

        in vec3 vertex_position;

        uniform mat4 view_matrix;
        uniform mat4 projection_matrix;

        out vec3 pos;

        void main() {
            gl_Position = projection_matrix * view_matrix * vec4(vertex_position, 1.0);
            pos = vertex_position;
        }
        """, """
        #version 150

        in vec3 pos;
        out vec4 frag_colour;

        void main() {
            vec3 pos_scaled = pos / 10.0;

            // https://www.ronja-tutorials.com/2018/05/18/Chessboard.html#checkerboard-in-2d-and-3d        
            float color = (int(floor(pos_scaled.x) + floor(pos_scaled.y) + floor(pos_scaled.z)) & 1) * 2.0;

            frag_colour = vec4(color, color, color, 0.1);
        }
        """)

        self.view_matrix_location = self.program.get_uniform_location("view_matrix")
        self.projection_matrix_location = self.program.get_uniform_location("projection_matrix")

        vertex_position_index = self.program.get_attrib_location("vertex_position")

        self.vertices = GlBuffer(self._vertices_from_dimensions(self.dimensions))

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

        with self.program:
            glUniformMatrix4fv(self.view_matrix_location, 1, GL_FALSE, self.view_matrix)
            glUniformMatrix4fv(self.projection_matrix_location, 1, GL_FALSE, self.projection_matrix)

            glBindVertexArray(self.vao)

            with self.vertices:
                glDrawArrays(GL_TRIANGLES, 0, len(self.vertices))

    @staticmethod
    def _vertices_from_dimensions(dimensions):
        result = []
        x = dimensions[0]
        y = dimensions[1]
        z = dimensions[2]

        result.append([-x/2, 0, z/2])
        result.append([x/2, 0, z/2])
        result.append([x/2, 0, -z/2])

        result.append([x/2, 0, -z/2])
        result.append([-x/2, 0, -z/2])
        result.append([-x/2, 0, z/2])

        result.append([-x/2, 0, -z/2])
        result.append([x/2, 0, -z/2])
        result.append([x/2, y, -z/2])

        result.append([x/2, y, -z/2])
        result.append([-x/2, y, -z/2])
        result.append([-x/2, 0, -z/2])

        return numpy.array(result, numpy.float32)