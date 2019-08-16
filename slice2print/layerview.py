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

import wx

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

    def on_slider(self, event):
        self.layer_label.SetLabelText(str(event.GetInt()))
        self.Layout()

    def set_model_mesh(self, model_mesh):
        self.gl_canvas.set_model_mesh(model_mesh)

    def view_all(self):
        self.gl_canvas.view_all()

    def set_layer_count(self, layer_count):
        self.slider.SetRange(1, layer_count)
        self.slider.SetValue(layer_count)
        self.slider.Enable(True)

        self.layer_label.SetLabelText(str(layer_count))

        self.Layout()