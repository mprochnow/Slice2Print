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

import enum
import math

from OpenGL.GL import *

import numpy
import numpy.linalg

import wx
import wx.glcanvas

import glhelpers
import glmesh


ProjectionType = enum.Enum("ProjectionType", "PERSPECTIVE ORTHOGRAPHIC")


class Camera:
    DEFAULT_YAW = 25.0
    DEFAULT_PITCH = 25.0

    def __init__(self, fov_y=22.5, projection_type=ProjectionType.ORTHOGRAPHIC):
        self.fov_y = fov_y
        self.projection_type = projection_type

        self.viewport_width = 0
        self.viewport_height = 0

        self.pos_x = 0.0
        self.pos_y = 0.0
        self.camera_distance = 140.0

        self.yaw = self.DEFAULT_YAW
        self.pitch = self.DEFAULT_PITCH

    def reset(self):
        self.pos_x = 0.0
        self.pos_y = 0.0
        self.camera_distance = 140.0

        self.yaw = self.DEFAULT_YAW
        self.pitch = self.DEFAULT_PITCH

    def move_x(self, x):
        self.pos_x += x

    def move_y(self, y):
        self.pos_y += y

    def zoom(self, z):
        if self.camera_distance - z >= 0:
            self.camera_distance -= z

    def rotate_x(self, degrees):
        self.pitch += degrees

    def rotate_y(self, degrees):
        self.yaw += degrees

    def update_viewport(self, x, y, width, height):
        glViewport(x, y, width, height)

        self.viewport_width = width
        self.viewport_height = height

    def get_projection_matrix(self):
        if self.projection_type == ProjectionType.PERSPECTIVE:
            return glhelpers.perspective(self.fov_y, self.viewport_width / self.viewport_height, 1.0, 1000.0)
        elif self.projection_type == ProjectionType.ORTHOGRAPHIC:
            dist = self.camera_distance
            aspect = self.viewport_width / self.viewport_height

            height = dist * math.tan(math.radians(self.fov_y / 2))
            width = height * aspect

            return glhelpers.orthographic(-width, width, -height, height, -100.0 * dist, 100.0 * dist)

    def _get_rotation_matrix(self):
        mr_x = glhelpers.rotate_x(self.pitch)
        mr_y = glhelpers.rotate_y(self.yaw)

        return numpy.dot(mr_y, mr_x)

    def get_view_matrix(self):
        translation_matrix = glhelpers.translate([self.pos_x, self.pos_y, -self.camera_distance])

        return numpy.dot(self._get_rotation_matrix(), translation_matrix)

    def view_all(self, bb):
        """
        Moves the camera to a position where to complete model is within the viewport.
        :param bb: Instance of model.BoundingBox
        """
        # Center camera vertical to mesh
        # The mesh's z position is already set to 0 via its model matrix, so we use the absolute value here
        self.pos_y = -abs((bb.z_min + bb.z_max) / 2)

        # Radius of bounding sphere
        r = numpy.linalg.norm(bb.diagonal()) / 2

        self.camera_distance = r / math.tan(math.radians(self.fov_y / 2))


class GlCanvas(wx.glcanvas.GLCanvas):
    CAMERA_SPEED_XY = 0.2
    CAMERA_SPEED_Z = 4.0
    CAMERA_SPEED_ROTATION = 1.0

    def __init__(self, parent):
        attributes = (wx.glcanvas.WX_GL_RGBA,
                      wx.glcanvas.WX_GL_DOUBLEBUFFER,
                      wx.glcanvas.WX_GL_SAMPLE_BUFFERS, 1,
                      wx.glcanvas.WX_GL_SAMPLES, 4,
                      wx.glcanvas.WX_GL_DEPTH_SIZE, 24)

        wx.glcanvas.GLCanvas.__init__(self, parent, attribList=attributes)
        self.context = wx.glcanvas.GLContext(self)
        self.initialized = False
        self.model_mesh = None
        self.camera = Camera()

        self.mouse_x = 0
        self.mouse_y = 0

        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_PAINT, self.on_paint)

        self.Bind(wx.EVT_LEFT_DOWN, self.on_left_down)
        self.Bind(wx.EVT_RIGHT_DOWN, self.on_right_down)
        self.Bind(wx.EVT_ENTER_WINDOW, self.on_enter_window)
        self.Bind(wx.EVT_MOTION, self.on_motion)
        self.Bind(wx.EVT_MOUSEWHEEL, self.on_mousewheel)

    def create_mesh(self, vertices, normals, indices, bounding_box):
        shader_program = glhelpers.ShaderProgram(glmesh.MODEL_VERTEX_SHADER, glmesh.MODEL_FRAGMENT_SHADER)
        self.model_mesh = glmesh.ModelMesh(shader_program, vertices, normals, indices, bounding_box)

        self.camera.reset()
        self.camera.view_all(bounding_box)

        self.Refresh()

    def draw(self):
        self.SetCurrent(self.context)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.model_mesh:
            self.model_mesh.update_projection_matrix(self.camera.get_projection_matrix())
            self.model_mesh.update_view_matrix(self.camera.get_view_matrix())
            self.model_mesh.draw()

        self.SwapBuffers()

    def on_size(self, event):
        self.SetCurrent(self.context)

        size = self.GetClientSize()
        self.camera.update_viewport(0, 0, size.width, size.height)

        self.Refresh(False)

    def on_paint(self, event):
        if not self.initialized:
            self.initialized = True

            glEnable(GL_DEPTH_TEST)
            glClearColor(1, 1, 0.9, 1)

        self.draw()

    def on_left_down(self, event):
        self.mouse_x = event.GetX()
        self.mouse_y = event.GetY()

    def on_right_down(self, event):
        self.mouse_x = event.GetX()
        self.mouse_y = event.GetY()

    def on_enter_window(self, event):
        self.mouse_x = event.GetX()
        self.mouse_y = event.GetY()

    def on_motion(self, event):
        if event.Dragging():
            mouse_x = event.GetX()
            mouse_y = event.GetY()

            dx = self.mouse_x - mouse_x
            dy = self.mouse_y - mouse_y

            if event.LeftIsDown() and not event.RightIsDown():
                self.camera.rotate_x(self.CAMERA_SPEED_ROTATION * -dy)
                self.camera.rotate_y(self.CAMERA_SPEED_ROTATION * -dx)

                self.Refresh()
            elif event.RightIsDown() and not event.LeftIsDown():
                self.camera.move_x(self.CAMERA_SPEED_XY * -dx)
                self.camera.move_y(self.CAMERA_SPEED_XY * dy)
                self.Refresh()

            self.mouse_x = mouse_x
            self.mouse_y = mouse_y

    def on_mousewheel(self, event):
        if event.GetWheelAxis() == wx.MOUSE_WHEEL_VERTICAL:
            self.camera.zoom(self.CAMERA_SPEED_Z * event.GetWheelRotation() // event.GetWheelDelta())
            self.Refresh()
