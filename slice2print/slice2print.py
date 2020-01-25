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

import dialog
import icons
import model
import settings
import modelview


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
                    with wx.BusyInfo("Loading model...", self.frame):
                        self.model = model.Model.from_file(filename)
                        self.frame.model_view.set_model(self.model)
                        self.show_model_mesh()

                    self.frame.status_bar.SetStatusText(
                        "Model size: {:.2f} x {:.2f} x {:.2f} mm".format(*self.model.dimensions))
                except (AssertionError, IOError, ValueError, struct.error) as e:
                    d = wx.MessageDialog(self.frame, str(e), "Error while open file", style=wx.OK | wx.ICON_ERROR)
                    d.ShowModal()

    def view_all(self):
        self.frame.model_view.view_all()

    def view_from_top(self):
        self.frame.model_view.view_from_top()

    def slice_model(self):
        slicer_config = self.settings.get_slicer_config()

        with dialog.SlicerDialog(self.frame, self.model, slicer_config) as dlg:
            if dlg.ShowModal() == wx.ID_OK:
                self.frame.model_view.set_sliced_model(dlg.get_sliced_model())
                self.show_layer_mesh()

    def show_model_mesh(self):
        self.frame.GetToolBar().ToggleTool(self.frame.tool_model_view.GetId(), True)
        self.frame.model_view.show_model_mesh()

    def show_layer_mesh(self):
        self.frame.GetToolBar().ToggleTool(self.frame.tool_layer_view.GetId(), True)
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


class ParameterPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent)

        sizer = wx.FlexGridSizer(0, 3, 0, 0)
        self.SetSizer(sizer)

    def on_update(self, event):
        raise NotImplementedError

    def add_spin_ctrl_double(self, label, min_, max_, unit="", offset_bottom=False):
        """
        Adds a wx.SpinCtrlDouble to the Panel and sets its event handler for wx.EVT_SPINCTRLDOUBLE to self.on_update.
        Control is configured with 2 digits and an increment of 0.1 for now.

        :param label: Text for label in front of control
        :param min_: Minimum value for the control
        :param max_: Maximum value for the control
        :param unit: Text for label behind the control
        :param offset_bottom: Should the control be rendered with a bottom margin
        :return: Instance of wx.SpinCtrlDouble
        """
        sizer = self.GetSizer()

        margin = wx.TOP
        if offset_bottom:
            margin |= wx.BOTTOM

        # Label in front of control
        sizer.Add(wx.StaticText(self, wx.ID_ANY, label), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | margin, 7)

        # The control itself
        ctrl = wx.SpinCtrlDouble(self, wx.ID_ANY, min=0.0, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        ctrl.SetDigits(2)
        ctrl.SetIncrement(0.1)
        sizer.Add(ctrl, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | margin, 7)

        # Label behind the control
        sizer.Add(wx.StaticText(self, wx.ID_ANY, "mm"), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT | margin, 7)

        ctrl.Bind(wx.EVT_SPINCTRLDOUBLE, self.on_update)

        return ctrl

    def add_spin_ctrl(self, label, min_, max_, unit="", offset_bottom=False):
        """
        Adds a wx.SpinCtrl to the Panel and sets its event handler for wx.EVT_SPINCTRL to self.on_update

        :param label: Text for label in front of control
        :param min_: Minimum value for the control
        :param max_: Maximum value for the control
        :param unit: Text for label behind the control
        :param offset_bottom: Should the control be rendered with a bottom margin
        :return: Instance of wx.SpinCtrl
        """
        sizer = self.GetSizer()

        margin = wx.TOP
        if offset_bottom:
            margin |= wx.BOTTOM

        # Label in front of control
        sizer.Add(wx.StaticText(self, wx.ID_ANY, label), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | margin, 7)

        # The control itself
        ctrl = wx.SpinCtrl(self, wx.ID_ANY, min=min_, max=max_, style=wx.ALIGN_RIGHT | wx.SP_ARROW_KEYS)
        sizer.Add(ctrl, 0, wx.EXPAND | wx.ALIGN_CENTER_VERTICAL | wx.LEFT | margin, 7)

        # Label behind control
        sizer.Add(wx.StaticText(self, wx.ID_ANY, unit), 0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.RIGHT | margin, 7)

        ctrl.Bind(wx.EVT_SPINCTRL, self.on_update)

        return ctrl


class PrintOptionsPanel(ParameterPanel):
    def __init__(self, parent, controller):
        self.controller = controller
        ParameterPanel.__init__(self, parent)

        self.ctrl_first_layer_height = self.add_spin_ctrl_double("First layer height", 0.0, 10.0, "mm")
        self.ctrl_layer_height = self.add_spin_ctrl_double("Layer height", 0.0, 10.0, "mm", True)

        self.ctrl_perimeters = self.add_spin_ctrl("Perimeters", 1, 100, "", True)

        self.ctrl_top_layers = self.add_spin_ctrl("Top layers", 0, 100)
        self.ctrl_bottom_layers = self.add_spin_ctrl("Bottom layers", 0, 100)
        self.ctrl_infill_angle = self.add_spin_ctrl("Infill angle", 0, 90, "°")
        self.ctrl_infill_overlap = self.add_spin_ctrl("Infill overlap", 0, 100, "%", True)

        self.ctrl_first_layer_speed = self.add_spin_ctrl("First layer speed", 1, 1000, "mm/sec")
        self.ctrl_first_layer_speed.Disable()
        self.ctrl_print_speed = self.add_spin_ctrl("Print speed", 1, 1000, "mm/sec")
        self.ctrl_print_speed.Disable()
        self.ctrl_travel_speed = self.add_spin_ctrl("Travel speed", 1, 10000, "mm/src", True)
        self.ctrl_travel_speed.Disable()

        self.Layout()

        self.controller.init_options(self)

    def on_update(self, event):
        self.controller.update_print_options(self)


class PrinterSettingsPanel(ParameterPanel):
    def __init__(self, parent, controller):
        self.controller = controller
        ParameterPanel.__init__(self, parent)

        self.ctrl_build_volume_width = self.add_spin_ctrl("Build volume width", 1, 1000, "mm")
        self.ctrl_build_volume_depth = self.add_spin_ctrl("Build volume depth", 1, 1000, "mm")
        self.ctrl_build_volume_height = self.add_spin_ctrl("Build volume height", 1, 1000, "mm", True)

        self.ctrl_nozzle_diameter = self.add_spin_ctrl_double("Nozzle diameter", 0.1, 2.0, "mm", True)

        self.ctrl_filament_diameter = self.add_spin_ctrl_double("Filament diameter", 1.0, 5.0, "mm", True)

        self.Layout()

        self.controller.init_printer_settings(self)

    def on_update(self, event):
        self.controller.update_printer_settings(self)
        pass


class MainFrame(wx.Frame):
    ACCEL_EXIT = wx.NewIdRef()

    def __init__(self):
        self.tool_model_view = None
        self.tool_layer_view = None
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

        self.model_view = modelview.ModelView(panel, self.settings.build_volume)

        self.settings_notebook = wx.Notebook(panel)
        self.print_options_panel = PrintOptionsPanel(self.settings_notebook, self.controller)
        self.printer_settings_panel = PrinterSettingsPanel(self.settings_notebook, self.controller)

        self.settings_notebook.AddPage(self.print_options_panel, "Options")
        self.settings_notebook.AddPage(self.printer_settings_panel, "Printer")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.model_view, 1, wx.EXPAND)
        sizer.Add(self.settings_notebook, 0, wx.EXPAND | wx.LEFT, 7)
        panel.SetSizer(sizer)
        self.Layout()

        self.Bind(wx.EVT_MENU, self.on_exit, id=MainFrame.ACCEL_EXIT)
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.SetAcceleratorTable(
            wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, MainFrame.ACCEL_EXIT)]))

        self.Maximize(self.settings.app_window_maximized)

    def create_toolbar(self):
        toolbar = self.CreateToolBar()
        tool_open = toolbar.AddTool(wx.ID_ANY, "Open model", icons.plussquare24.GetBitmap(), shortHelp="Open model")
        toolbar.AddSeparator()
        tool_slice = toolbar.AddTool(wx.ID_ANY, "Slice model", icons.play24.GetBitmap(), shortHelp="Slice model")
        toolbar.AddSeparator()
        self.tool_model_view = toolbar.AddRadioTool(
            wx.ID_ANY, "Model view", icons.box.GetBitmap(), shortHelp="Model view")
        self.tool_layer_view = toolbar.AddRadioTool(
            wx.ID_ANY, "Layer view", icons.boxsliced24.GetBitmap(), shortHelp="Layer view")
        toolbar.AddSeparator()
        tool_view_all = toolbar.AddTool(wx.ID_ANY, "View all", icons.maximize.GetBitmap(), shortHelp="View all")
        tool_view_from_top = toolbar.AddTool(
            wx.ID_ANY, "View from top", icons.boxtop24.GetBitmap(), shortHelp="View from top")
        toolbar.Realize()

        self.Bind(wx.EVT_TOOL, self.on_open, id=tool_open.GetId())
        self.Bind(wx.EVT_TOOL, self.on_view_all, id=tool_view_all.GetId())
        self.Bind(wx.EVT_TOOL, self.on_slice, id=tool_slice.GetId())
        self.Bind(wx.EVT_TOOL, self.on_model_view, id=self.tool_model_view.GetId())
        self.Bind(wx.EVT_TOOL, self.on_layer_view, id=self.tool_layer_view.GetId())
        self.Bind(wx.EVT_TOOL, self.on_view_from_top, id=tool_view_from_top.GetId())

        return toolbar

    def on_exit(self, event):
        self.Close()

    def on_open(self, event):
        self.controller.open_model()

    def on_view_all(self, event):
        self.controller.view_all()

    def on_view_from_top(self, event):
        self.controller.view_from_top()

    def on_slice(self, event):
        self.controller.slice_model()

    def on_model_view(self, event):
        self.controller.show_model_mesh()

    def on_layer_view(self, event):
        self.controller.show_layer_mesh()

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
