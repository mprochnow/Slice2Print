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

import glview
import glmesh
import layermesh


class ModelView(wx.Panel):
    def __init__(self, parent, build_volume):
        wx.Panel.__init__(self, parent)

        self.gl_canvas = glview.GlCanvas(self)
        self.layer_label = wx.StaticText(self, wx.ID_ANY, "Layer:")
        self.layer_no_label = wx.StaticText(self, wx.ID_ANY, "1", style=wx.EXPAND | wx.ALIGN_CENTER_HORIZONTAL)
        self.layer_slider = wx.Slider(self, wx.ID_ANY, 1, 1, 2, style=wx.SL_INVERSE | wx.SL_LEFT | wx.SL_VERTICAL)

        # Layer slider
        slider_sizer = wx.BoxSizer(wx.VERTICAL)
        slider_sizer.Add(self.layer_label, 0, wx.ALIGN_CENTER_HORIZONTAL)
        slider_sizer.Add(self.layer_no_label, 0, wx.ALIGN_CENTER_HORIZONTAL)
        slider_sizer.Add(self.layer_slider, 1, wx.ALIGN_CENTER_HORIZONTAL)

        # Bring it all together
        h_sizer = wx.BoxSizer(wx.HORIZONTAL)
        h_sizer.Add(self.gl_canvas, 1, wx.EXPAND)
        h_sizer.Add(slider_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 7)
        self.SetSizer(h_sizer)
        self.Layout()

        self.Bind(wx.EVT_SLIDER, self.on_layer_slider, id=self.layer_slider.GetId())

        self.layer_label.Disable()
        self.layer_no_label.Disable()
        self.layer_slider.Disable()
        self.gl_canvas.set_platform_mesh(glmesh.PlatformMesh(build_volume))

    def on_layer_slider(self, event):
        layer = event.GetInt()

        self.layer_no_label.SetLabelText(str(layer))
        self.Layout()

        self.gl_canvas.layer_mesh.set_layers_to_draw(layer)
        self.gl_canvas.Refresh()

    def set_build_volume(self, build_volume):
        self.gl_canvas.set_dimensions(build_volume)

    def set_model(self, model):
        self.gl_canvas.set_model_mesh(glmesh.ModelMesh(model))
        self.show_model_mesh()
        self.view_all()

    def set_sliced_model(self, sliced_model):
        self.gl_canvas.set_layer_mesh(layermesh.LayerMesh(sliced_model))
        self.show_layer_mesh()
        self.view_all()

        self.layer_slider.SetRange(1, sliced_model.layer_count)
        self.layer_slider.SetValue(sliced_model.layer_count)
        self.layer_no_label.SetLabelText(str(sliced_model.layer_count))

        self.Layout()

    def view_all(self):
        self.gl_canvas.view_all()

    def show_model_mesh(self):
        self.layer_label.Disable()
        self.layer_no_label.Disable()
        self.layer_slider.Disable()

        self.gl_canvas.show_model_mesh()

    def show_layer_mesh(self):
        self.layer_label.Enable()
        self.layer_no_label.Enable()
        self.layer_slider.Enable()

        self.gl_canvas.show_layer_mesh()