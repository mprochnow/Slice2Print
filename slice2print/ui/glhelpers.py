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

import math

import numpy

from OpenGL.GL import *
from OpenGL.GL import shaders
from OpenGL.arrays import ArrayDatatype


def normalize(vector):
    return vector / numpy.linalg.norm(vector)


def rotate_x(deg):
    rad = math.radians(deg)

    m = numpy.identity(4, numpy.float32)
    m[1][1] = math.cos(rad)
    m[1][2] = math.sin(rad)
    m[2][1] = -math.sin(rad)
    m[2][2] = math.cos(rad)

    return m


def rotate_y(deg):
    rad = math.radians(deg)

    m = numpy.identity(4, numpy.float32)
    m[0][0] = math.cos(rad)
    m[0][2] = -math.sin(rad)
    m[2][0] = math.sin(rad)
    m[2][2] = math.cos(rad)

    return m


def translate(position):
    m = numpy.identity(4, numpy.float32)
    m[3][0] = position[0]
    m[3][1] = position[1]
    m[3][2] = position[2]

    return m


def perspective(fov_y, aspect, near, far):
    r = math.tan(math.radians(fov_y) * 0.5) * near
    sx = (2 * near) / (r * aspect + r * aspect)
    sy = near / r
    sz = -(far + near) / (far - near)
    pz = -(2 * far * near) / (far-near)

    return numpy.array([[sx, 0.0, 0.0, 0.0],
                        [0.0, sy, 0.0, 0.0],
                        [0.0, 0.0, sz, -1.0],
                        [0.0, 0.0, pz, 0.0]], numpy.float32)


def orthographic(left, right, bottom, top, near, far):
    sx = 2 / (right - left)
    sy = 2 / (top - bottom)
    sz = -2 / (far - near)

    tx = - (right + left) / (right - left)
    ty = - (top + bottom) / (top - bottom)
    tz = - (far + near) / (far - near)

    return numpy.array([[sx, 0.0, 0.0, 0.0],
                        [0.0, sy, 0.0, 0.0],
                        [0.0, 0.0, sz, 0.0],
                        [tx, ty, tz, 1.0]], numpy.float32)


class ShaderProgram:
    def __init__(self, vertex_shader, fragment_shader):
        self.program = shaders.compileProgram(
            shaders.compileShader(vertex_shader, GL_VERTEX_SHADER),
            shaders.compileShader(fragment_shader, GL_FRAGMENT_SHADER)
        )

        # max_index = int(glGetProgramiv(self.program, GL_ACTIVE_ATTRIBUTES))
        # for i in range(max_index):
        #     name, size, type = glGetActiveAttrib(self.program, i)
        #     print("Attribute", i, name, size, type)

        self.uniforms = dict()

        for index in range(int(glGetProgramiv(self.program, GL_ACTIVE_UNIFORMS))):
            uniform_name, size, uniform_type = glGetActiveUniform(self.program, index)
            uniform_name = uniform_name.decode("ascii")
            location = glGetUniformLocation(self.program, uniform_name)
            self.uniforms[uniform_name] = (location, uniform_type)

    def __setattr__(self, name, value):
        try:
            location, uniform_type = self.uniforms[name]

            if uniform_type == GL_FLOAT_MAT4:
                glUniformMatrix4fv(location, 1, GL_FALSE, value)
            elif uniform_type == GL_FLOAT_VEC4:
                glUniform4fv(location, 1, value)
            else:
                raise RuntimeError("Uniform type %s not supported" % uniform_type)
        except AttributeError:
            object.__setattr__(self, name, value)

    def get_attrib_location(self, name):
        return glGetAttribLocation(self.program, name)

    def __enter__(self):
        glUseProgram(self.program)

    def __exit__(self, typ, val, tb):
        glUseProgram(0)


class GlBuffer:
    def __init__(self, data=None, target=None):
        self.data = None
        self.target = None
        self.vbo = glGenBuffers(1)

        if data is not None:
            self.set_data(data, target)

    def delete(self):
        glDeleteBuffers(1, [self.vbo])

    def set_data(self, data, target):
        self.data = data
        self.target = target

        glBindBuffer(self.target, self.vbo)
        glBufferData(self.target,
                     ArrayDatatype.arrayByteCount(self.data),
                     ArrayDatatype.voidDataPointer(self.data),
                     GL_STATIC_DRAW)
        glBindBuffer(self.target, 0)

    def __len__(self):
        return len(self.data)

    def __enter__(self):
        glBindBuffer(self.target, self.vbo)

    def __exit__(self, typ, val, tb):
        glBindBuffer(self.target, 0)
