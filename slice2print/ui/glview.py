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

from OpenGL.GL import *

import numpy
import numpy.linalg

import wx
import wx.glcanvas

from ui import glhelpers
import model


class Camera:
    DEFAULT_YAW = 25.0
    DEFAULT_PITCH = 25.0
    DEFAULT_CAMERA_DISTANCE = 140.0

    def __init__(self, fov_y=22.5):
        self.fov_y = fov_y
        self.viewport_width = 0
        self.viewport_height = 0

        self.pos_x = 0.0
        self.pos_y = 0.0

        self.max_camera_distance = float("inf")
        self.camera_distance = self.DEFAULT_CAMERA_DISTANCE
        self.yaw = self.DEFAULT_YAW
        self.pitch = self.DEFAULT_PITCH

    def move_x(self, x):
        self.pos_x += x

    def move_y(self, y):
        self.pos_y += y

    def zoom(self, z):
        camera_distance = self.camera_distance - z

        if 0.0 < camera_distance < self.max_camera_distance:
            self.camera_distance = camera_distance

    def rotate_x(self, degrees):
        self.pitch += degrees

    def rotate_y(self, degrees):
        self.yaw += degrees

    def update_viewport(self, x, y, width, height):
        glViewport(x, y, width, height)

        self.viewport_width = width
        self.viewport_height = height

    def get_projection_matrix(self):
        dist = self.camera_distance
        aspect = self.viewport_width / self.viewport_height

        height = dist * math.tan(math.radians(self.fov_y / 2))
        width = height * aspect

        return glhelpers.orthographic(-width, width, -height, height, -100.0 * dist, 100.0 * dist)

    def _get_rotation_matrix(self):
        mr_x = glhelpers.rotate_x(self.pitch)
        mr_y = glhelpers.rotate_y(self.yaw)

        return numpy.matmul(mr_y, mr_x)

    def get_view_matrix(self):
        translation_matrix = glhelpers.translate([self.pos_x, self.pos_y, -self.camera_distance])

        return numpy.matmul(self._get_rotation_matrix(), translation_matrix)

    def view_all(self, bb):
        """
        Moves the camera to a position where the complete model is within the viewport.
        :param bb: Instance of model.BoundingBox
        """

        self.pos_x = 0.0
        # Center camera vertical to mesh (the mesh's z position is already set to 0 via its model matrix)
        self.pos_y = -(bb.z_max - bb.z_min) / 2
        self.yaw = self.DEFAULT_YAW
        self.pitch = self.DEFAULT_PITCH

        # Radius of bounding sphere
        r = numpy.linalg.norm(bb.diagonal()) / 2

        self.camera_distance = r / math.tan(math.radians(self.fov_y / 2))

    def view_from_top(self):
        self.yaw = 0.0
        self.pitch = 90.0

    def set_current_camera_distance_as_max(self):
        self.max_camera_distance = self.camera_distance


class GlCanvas(wx.glcanvas.GLCanvas):
    CAMERA_SPEED_XY = 0.2
    CAMERA_SPEED_Z = 10.0
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
        self.platform_mesh = None
        self.model_mesh = None
        self.layer_mesh = None
        self.display_layer_mesh = False
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

    def set_platform_mesh(self, platform_mesh):
        self.platform_mesh = platform_mesh

    def set_dimensions(self, build_volume):
        if self.platform_mesh:
            self.platform_mesh.set_dimensions(build_volume)

    def set_model_mesh(self, model_mesh):
        if self.model_mesh:
            self.model_mesh.delete()
        self.model_mesh = model_mesh

    def set_layer_mesh(self, layer_mesh):
        if self.layer_mesh:
            self.layer_mesh.delete()
        self.layer_mesh = layer_mesh

    def show_model_mesh(self):
        self.display_layer_mesh = False
        self.Refresh()

    def show_layer_mesh(self):
        self.display_layer_mesh = True
        self.Refresh()

    def view_all(self):
        if self.model_mesh:
            self.camera.view_all(self.model_mesh.bounding_box)
            self.Refresh()

    def view_from_top(self):
        self.camera.view_from_top()
        self.Refresh()

    def draw(self):
        self.SetCurrent(self.context)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        if self.model_mesh and not self.display_layer_mesh:
            self.model_mesh.update_projection_matrix(self.camera.get_projection_matrix())
            self.model_mesh.update_view_matrix(self.camera.get_view_matrix())
            self.model_mesh.draw()

        if self.layer_mesh and self.display_layer_mesh:
            self.layer_mesh.update_projection_matrix(self.camera.get_projection_matrix())
            self.layer_mesh.update_view_matrix(self.camera.get_view_matrix())
            self.layer_mesh.draw()

        if self.platform_mesh:
            self.platform_mesh.update_projection_matrix(self.camera.get_projection_matrix())
            self.platform_mesh.update_view_matrix(self.camera.get_view_matrix())
            self.platform_mesh.draw()

        self.SwapBuffers()

    def update_viewport(self):
        self.SetCurrent(self.context)

        size = self.GetClientSize()
        self.camera.update_viewport(0, 0, size.width, size.height)

        self.Refresh()

    def on_size(self, event):
        if self.IsShownOnScreen():
            self.update_viewport()

    def on_paint(self, event):
        if not self.initialized:
            self.initialized = True
            self.SetCurrent(self.context)

            glEnable(GL_DEPTH_TEST)

            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            glClearColor(1, 1, 0.9, 1)

            self.update_viewport()

            if self.platform_mesh:
                d = self.platform_mesh.dimensions
                bb = model.BoundingBox()
                bb.set_boundaries(-d[0]/2, d[0]/2, -d[2]/2, d[2]/2, -d[1]/2, d[1]/2)
                self.camera.view_all(bb)
                self.camera.set_current_camera_distance_as_max()

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
