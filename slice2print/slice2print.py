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
import sys

import numpy
import wx

import dialog
import glmesh
import glview
import icons
import model
import settings
import slicedview


class MainFrameController:
    def __init__(self, frame, settings):
        self.frame = frame
        self.settings = settings
        self.model = None

    def open_model(self):
        with wx.FileDialog(self.frame, "Open model", wildcard="3D model (*.stl)|*.stl|All files (*.*)|*.*",
                           style=wx.FD_FILE_MUST_EXIST) as dlg:
            if dlg.ShowModal() != wx.ID_CANCEL:
                filename = dlg.GetPath()
                try:
                    self.frame.notebook.SetSelection(0)

                    self.model = model.Model.from_file(filename)
                    self.frame.model_view.set_model_mesh(glmesh.ModelMesh(self.model))
                    self.frame.model_view.view_all()

                    self.frame.status_bar.SetStatusText(
                        "Model size: {:.2f} x {:.2f} x {:.2f} mm".format(*self.model.dimensions))
                except Exception as e:
                    d = wx.MessageDialog(self, str(e), "Error while open file", style=wx.OK | wx.ICON_ERROR)
                    d.ShowModal()

    def view_all(self):
        page = self.frame.notebook.GetSelection()
        if page == 0:
            self.frame.model_view.view_all()
        elif page == 1:
            self.frame.sliced_view.view_all()

    def slice_model(self):
        slicer_config = self.settings.get_slicer_config()

        with dialog.SlicerDialog(self.frame, self.model, slicer_config) as dlg:
            if dlg.slice_model() == wx.ID_OK:
                self.frame.notebook.SetSelection(1)

                mesh = glmesh.LayerMesh.from_sliced_model(dlg.slicer.sliced_model, self.model.bounding_box)

                self.frame.sliced_view.set_model_mesh(mesh)
                self.frame.sliced_view.view_all()
                self.frame.sliced_view.set_layer_count(dlg.slicer.sliced_model.layer_count)

    def settings_dialog(self):
        with dialog.SettingsDialog(self.frame) as dlg:
            dlg.set_build_volume(self.settings.build_volume)
            dlg.set_nozzle_diameter(self.settings.nozzle_diameter)
            dlg.set_filament_diameter(self.settings.filament_diameter)

            if dlg.ShowModal() != wx.ID_CANCEL:
                build_volume = self.settings.build_volume = dlg.get_build_volume()
                self.settings.nozzle_diameter = dlg.get_nozzle_diameter()
                self.settings.filament_diameter = dlg.get_filament_diameter()

                self.frame.model_view.platform_mesh.set_dimensions(build_volume)
                self.frame.Refresh()

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

    def init_options(self, options_panel):
        options_panel.ctrl_first_layer_height.SetValue(self.settings.first_layer_height)
        options_panel.ctrl_layer_height.SetValue(self.settings.layer_height)
        options_panel.ctrl_first_layer_speed.SetValue(self.settings.first_layer_speed)
        options_panel.ctrl_print_speed.SetValue(self.settings.print_speed)
        options_panel.ctrl_travel_speed.SetValue(self.settings.travel_speed)
        options_panel.ctrl_perimeters.SetValue(self.settings.perimeters)

    def update_options(self, options_panel):
        self.settings.first_layer_height = options_panel.ctrl_first_layer_height.GetValue()
        self.settings.layer_height = options_panel.ctrl_layer_height.GetValue()
        self.settings.first_layer_speed = options_panel.ctrl_first_layer_speed.GetValue()
        self.settings.print_speed = options_panel.ctrl_print_speed.GetValue()
        self.settings.travel_speed = options_panel.ctrl_travel_speed.GetValue()
        self.settings.perimeters = options_panel.ctrl_perimeters.GetValue()


class OptionsPanel(wx.Panel):
    def __init__(self, parent, controller):
        self.controller = controller
        wx.Panel.__init__(self, parent)

        sizer = wx.FlexGridSizer(0, 3, 0, 0)

        # First layer height
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "First layer height"), 0, wx.ALIGN_CENTER_VERTICAL| wx.TOP, 7)

        self.ctrl_first_layer_height = wx.SpinCtrlDouble(self, wx.ID_ANY, min=0.0, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        self.ctrl_first_layer_height.SetDigits(2)
        self.ctrl_first_layer_height.SetIncrement(0.1)
        sizer.Add(self.ctrl_first_layer_height, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, "mm"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        # Layer height
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Layer height"), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.BOTTOM, 7)

        self.ctrl_layer_height = wx.SpinCtrlDouble(self, wx.ID_ANY, min=0.0, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        self.ctrl_layer_height.SetDigits(2)
        self.ctrl_layer_height.SetIncrement(0.1)
        sizer.Add(self.ctrl_layer_height, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.BOTTOM, 7)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, "mm"), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        # Perimeters
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Perimeters"), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP | wx.BOTTOM, 7)

        self.ctrl_perimeters = wx.SpinCtrl(self, wx.ID_ANY, min=1, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        sizer.Add(self.ctrl_perimeters, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.BOTTOM, 7)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, ""), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        # First layer speed
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "First layer speed"), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP, 7)

        self.ctrl_first_layer_speed = wx.SpinCtrl(self, wx.ID_ANY, min=1, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        sizer.Add(self.ctrl_first_layer_speed, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, "mm/sec"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        # Print speed
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Print speed"), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP, 7)

        self.ctrl_print_speed = wx.SpinCtrl(self, wx.ID_ANY, min=1, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        sizer.Add(self.ctrl_print_speed, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, "mm/sec"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        # Travel speed
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "Travel speed"), 0, wx.ALIGN_CENTER_VERTICAL | wx.TOP, 7)

        self.ctrl_travel_speed = wx.SpinCtrl(self, wx.ID_ANY, min=1, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        sizer.Add(self.ctrl_travel_speed, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        sizer.Add(wx.StaticText(self, wx.ID_ANY, "mm/sec"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        self.SetSizer(sizer)
        self.Layout()

        self.ctrl_first_layer_height.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_update)
        self.ctrl_layer_height.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_update)
        self.ctrl_first_layer_speed.Bind(wx.EVT_SPINCTRL, self.on_update)
        self.ctrl_print_speed.Bind(wx.EVT_SPINCTRL, self.on_update)
        self.ctrl_travel_speed.Bind(wx.EVT_SPINCTRL, self.on_update)
        self.ctrl_perimeters.Bind(wx.EVT_SPINCTRL, self.on_update)

        self.controller.init_options(self)

    def on_update(self, event):
        self.controller.update_options(self)


class MainFrame(wx.Frame):
    ACCEL_EXIT = wx.NewIdRef()

    def __init__(self):
        self.settings = settings.Settings()
        self.settings.load_from_file()
        self.controller = MainFrameController(self, self.settings)

        wx.Frame.__init__(self, None, title="Slice2Print", size=self.settings.app_window_size)

        self.SetMinSize((640, 480))

        self.toolbar = self.create_toolbar()
        self.status_bar = self.CreateStatusBar(1)
        sizer = wx.BoxSizer()
        panel = wx.Panel(self, wx.ID_ANY)
        sizer.Add(panel, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.options_panel = OptionsPanel(panel, self.controller)

        self.notebook = wx.Notebook(panel)
        self.model_view = glview.GlCanvas(self.notebook)
        self.sliced_view = slicedview.SlicedView(self.notebook, self.settings.build_volume)

        self.notebook.AddPage(self.model_view, "3D Model")
        self.notebook.AddPage(self.sliced_view, "Sliced Model")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.options_panel, 0, wx.EXPAND | wx.LEFT, 7)
        sizer.Add(self.notebook, 1, wx.EXPAND | wx.LEFT, 7)
        panel.SetSizer(sizer)
        self.Layout()

        self.Bind(wx.EVT_MENU, self.on_exit, id=MainFrame.ACCEL_EXIT)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.SetAcceleratorTable(
            wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, MainFrame.ACCEL_EXIT)]))

        self.Maximize(self.settings.app_window_maximized)

        self.model_view.set_platform_mesh(glmesh.PlatformMesh(self.settings.build_volume))

    def create_toolbar(self):
        toolbar = self.CreateToolBar()
        tool_open = toolbar.AddTool(wx.ID_ANY, "", icons.folder24.GetBitmap(), shortHelp="Open")
        toolbar.AddSeparator()
        tool_view_all = toolbar.AddTool(wx.ID_ANY, "", icons.maximize.GetBitmap(), shortHelp="View all")
        tool_slice = toolbar.AddTool(wx.ID_ANY, "", icons.play24.GetBitmap(), shortHelp="Slice")
        toolbar.AddStretchableSpace()
        tool_settings = toolbar.AddTool(wx.ID_ANY, "", icons.settings24.GetBitmap(), shortHelp="Settings")
        toolbar.Realize()

        self.Bind(wx.EVT_TOOL, self.on_open, id=tool_open.GetId())
        self.Bind(wx.EVT_TOOL, self.on_view_all, id=tool_view_all.GetId())
        self.Bind(wx.EVT_TOOL, self.on_slice, id=tool_slice.GetId())
        self.Bind(wx.EVT_TOOL, self.on_settings, id=tool_settings.GetId())

        return toolbar

    def on_exit(self, event):
        self.Close()

    def on_open(self, event):
        self.controller.open_model()

    def on_view_all(self, event):
        self.controller.view_all()

    def on_slice(self, event):
        self.controller.slice_model()

    def on_settings(self, event):
        self.controller.settings_dialog()

    def on_size(self, event):
        self.controller.frame_size_changed()
        event.Skip()

    def on_close(self, event):
        self.controller.close_frame()


if __name__ == "__main__":
    if sys.platform == "win32":
        # https://docs.microsoft.com/en-us/windows/desktop/api/Winuser/nf-winuser-setthreaddpiawarenesscontext
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

        # https://github.com/prusa3d/PrusaSlicer/blob/563a1a8441dbb7586a167c4bdce0e083e3774980/src/slic3r/GUI/GUI_Utils.hpp#L39
        # https://github.com/prusa3d/PrusaSlicer/blob/eebb9e3fe79cbda736bf95349c5c403ec4aef184/src/slic3r/GUI/GUI_App.cpp#L90
        # https://github.com/prusa3d/PrusaSlicer/blob/563a1a8441dbb7586a167c4bdce0e083e3774980/src/slic3r/GUI/GUI_Utils.hpp#L55

    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
