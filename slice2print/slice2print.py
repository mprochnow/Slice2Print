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

import ctypes
import struct
import sys

import wx

import model
import settings

import ui


class MainFrameController:
    def __init__(self):
        self.model = None
        self.settings = settings.Settings()
        self.settings.load_from_file()

        self.app = wx.App()
        self.frame = ui.MainFrame(self, self.settings)
        self.toolbar = ui.MainFrameToolBar(self.frame, self)
        self.frame.SetToolBar(self.toolbar)
        self.frame.SetDropTarget(ui.MainFrameFileDropTarget(self.on_drop_files))

    def main(self):
        self.frame.Show()
        self.app.MainLoop()

    def on_drop_files(self, filenames):
        if filenames:
            self._load_file(filenames[0])

    def load_model(self, event=None):
        with wx.FileDialog(self.frame, "Load model", wildcard="3D model (*.stl)|*.stl|All files (*.*)|*.*",
                           style=wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() != wx.ID_CANCEL:
                self._load_file(dlg.GetPath())

    def _load_file(self, filename):
        try:
            with wx.BusyInfo("Loading model...", self.frame):
                self.model = model.Model.from_file(filename)
                self.frame.model_view.set_model(self.model)
                self.show_model_mesh()

            self.toolbar.enable_model_tools()
            self.frame.status_bar.SetStatusText(
                "Model size: {:.2f} x {:.2f} x {:.2f} mm".format(*self.model.dimensions))
        except (AssertionError, IOError, ValueError, struct.error) as e:
            d = wx.MessageDialog(self.frame, str(e), "Error while open file", style=wx.OK | wx.ICON_ERROR)
            d.ShowModal()
            return False
        return True

    def view_all(self, event=None):
        self.frame.model_view.view_all()

    def view_from_top(self, event=None):
        self.frame.model_view.view_from_top()

    def slice_model(self, event=None):
        if self.model:
            slicer_config = self.settings.get_slicer_config()

            with ui.SlicerDialog(self.frame, self.model, slicer_config) as dlg:
                if dlg.ShowModal() == wx.ID_OK:
                    self.frame.model_view.set_sliced_model(dlg.get_sliced_model())
                    self.toolbar.enable_layer_view_tool()
                    self.show_layer_mesh()

    def show_model_mesh(self, event=None):
        self.toolbar.toggle_model_view()
        self.frame.model_view.show_model_mesh()

    def show_layer_mesh(self, event=None):
        self.toolbar.toggle_layer_view()
        self.frame.model_view.show_layer_mesh()

    def frame_size_changed(self):
        if self.frame.IsMaximized():
            self.settings.app_window_maximized = True
        else:
            self.settings.app_window_maximized = False
            self.settings.app_window_size = self.frame.GetSize()

    def close_frame(self):
        try:
            self.settings.save()
        except IOError:
            pass

        # Application does not close if window is minimized
        if self.frame.IsIconized():
            self.frame.Restore()

        self.frame.Destroy()

    def init_options(self, panel):
        panel.ctrl_first_layer_height.SetValue(self.settings.first_layer_height)
        panel.ctrl_layer_height.SetValue(self.settings.layer_height)
        panel.ctrl_first_layer_speed.SetValue(self.settings.first_layer_speed)
        panel.ctrl_print_speed.SetValue(self.settings.print_speed)
        panel.ctrl_travel_speed.SetValue(self.settings.travel_speed)
        panel.ctrl_perimeters.SetValue(self.settings.perimeters)
        panel.ctrl_top_layers.SetValue(self.settings.top_layers)
        panel.ctrl_bottom_layers.SetValue(self.settings.bottom_layers)
        panel.ctrl_infill_overlap.SetValue(self.settings.infill_overlap)
        panel.ctrl_infill_angle.SetValue(self.settings.infill_angle)

    def update_print_options(self, panel):
        self.settings.first_layer_height = panel.ctrl_first_layer_height.GetValue()
        self.settings.layer_height = panel.ctrl_layer_height.GetValue()
        self.settings.first_layer_speed = panel.ctrl_first_layer_speed.GetValue()
        self.settings.print_speed = panel.ctrl_print_speed.GetValue()
        self.settings.travel_speed = panel.ctrl_travel_speed.GetValue()
        self.settings.perimeters = panel.ctrl_perimeters.GetValue()
        self.settings.top_layers = panel.ctrl_top_layers.GetValue()
        self.settings.bottom_layers = panel.ctrl_bottom_layers.GetValue()
        self.settings.infill_overlap = panel.ctrl_infill_overlap.GetValue()
        self.settings.infill_angle = panel.ctrl_infill_angle.GetValue()

    def init_printer_settings(self, panel):
        width, depth, height = self.settings.build_volume

        panel.ctrl_build_volume_width.SetValue(width)
        panel.ctrl_build_volume_depth.SetValue(depth)
        panel.ctrl_build_volume_height.SetValue(height)
        panel.ctrl_nozzle_diameter.SetValue(self.settings.nozzle_diameter)
        panel.ctrl_filament_diameter.SetValue(self.settings.filament_diameter)

    def update_printer_settings(self, panel):
        width = panel.ctrl_build_volume_width.GetValue()
        depth = panel.ctrl_build_volume_depth.GetValue()
        height = panel.ctrl_build_volume_height.GetValue()
        build_volume = (width, depth, height)

        self.settings.build_volume = build_volume
        self.settings.nozzle_diameter = panel.ctrl_nozzle_diameter.GetValue()
        self.settings.filament_diameter = panel.ctrl_filament_diameter.GetValue()

        self.frame.model_view.set_build_volume(build_volume)
        self.frame.Refresh()


if __name__ == "__main__":
    if sys.platform == "win32":
        # https://docs.microsoft.com/en-us/windows/desktop/api/Winuser/nf-winuser-setthreaddpiawarenesscontext
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

        # https://github.com/prusa3d/PrusaSlicer/blob/563a1a8441dbb7586a167c4bdce0e083e3774980/src/slic3r/GUI/GUI_Utils.hpp#L39
        # https://github.com/prusa3d/PrusaSlicer/blob/eebb9e3fe79cbda736bf95349c5c403ec4aef184/src/slic3r/GUI/GUI_App.cpp#L90
        # https://github.com/prusa3d/PrusaSlicer/blob/563a1a8441dbb7586a167c4bdce0e083e3774980/src/slic3r/GUI/GUI_Utils.hpp#L55

    MainFrameController().main()
