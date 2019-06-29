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

import numpy
import wx

import glmesh
import glview
import icons
import model
import slicer
import settings
import settingsdialog


class MainFrame(wx.Frame):
    ACCEL_EXIT = wx.NewIdRef()

    def __init__(self):
        self.settings = settings.Settings()
        self.settings.load_from_file()

        self.model = None
        self.slicer = None

        wx.Frame.__init__(self, None, title="Slice2Print", size=self.settings.app_window_size)
        self.SetMinSize((640, 480))

        self.toolbar = self.CreateToolBar()
        self.tool_open = self.toolbar.AddTool(wx.ID_ANY, "", icons.folder24.GetBitmap(), shortHelp="Open")
        self.toolbar.AddSeparator()
        self.tool_view_all = self.toolbar.AddTool(wx.ID_ANY, "", icons.maximize.GetBitmap(), shortHelp="View all")
        self.tool_slice = self.toolbar.AddTool(wx.ID_ANY, "", icons.play24.GetBitmap(), shortHelp="Slice")
        self.toolbar.AddStretchableSpace()
        self.tool_settings = self.toolbar.AddTool(wx.ID_ANY, "", icons.settings24.GetBitmap(), shortHelp="Settings")
        self.toolbar.Realize()

        self.statusbar = self.CreateStatusBar(1)

        self.notebook = wx.Notebook(self)
        self.model_view = glview.GlCanvas(self.notebook)
        self.layer_view = glview.GlCanvas(self.notebook)

        self.notebook.AddPage(self.model_view, "3D Model")
        self.notebook.AddPage(self.layer_view, "Sliced Model")

        sizer = wx.BoxSizer()
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_MENU, self.on_exit, id=MainFrame.ACCEL_EXIT)
        self.Bind(wx.EVT_TOOL, self.on_open, id=self.tool_open.GetId())
        self.Bind(wx.EVT_TOOL, self.on_view_all, id=self.tool_view_all.GetId())
        self.Bind(wx.EVT_TOOL, self.on_slice, id=self.tool_slice.GetId())
        self.Bind(wx.EVT_TOOL, self.on_settings, id=self.tool_settings.GetId())
        self.Bind(wx.EVT_SIZE, self.on_size)
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.SetAcceleratorTable(
            wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, MainFrame.ACCEL_EXIT),
                                 wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("O"), self.tool_open.GetId())]))

        self.Layout()
        self.Maximize(self.settings.app_window_maximized)

        self.model_view.set_platform_mesh(glmesh.PlatformMesh(self.settings.build_volume))
        self.layer_view.set_platform_mesh(glmesh.PlatformMesh(self.settings.build_volume))

    def on_exit(self, event):
        self.Close()

    def on_open(self, event):
        with wx.FileDialog(self, "Open model", wildcard="3D model (*.stl)|*.stl|All files (*.*)|*.*",
                           style=wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_CANCEL:
                filename = dialog.GetPath()
                try:
                    self.notebook.SetSelection(0)

                    self.model = model.Model.from_file(filename)
                    self.model_view.set_model_mesh(glmesh.ModelMesh(self.model))
                    self.model_view.view_all()

                    self.statusbar.SetStatusText(
                        "Model size: {:.2f} x {:.2f} x {:.2f} mm".format(*self.model.dimensions))

                    self.slicer = slicer.Slicer(self.model)
                except Exception as e:
                    d = wx.MessageDialog(self, str(e), "Error while open file", style=wx.OK | wx.ICON_ERROR)
                    d.ShowModal()

    def on_view_all(self, event):
        page = self.notebook.GetSelection()
        if page == 0:
            self.model_view.view_all()
        elif page == 1:
            self.layer_view.view_all()

    def on_slice(self, event):
        self.layer_view.set_model_mesh(None)
        self.notebook.SetSelection(1)

        segments = self.slicer.slice(0.3, 0.2)
        segments = numpy.array(segments, numpy.float32).flatten()
        segments = segments.astype(numpy.float32) / slicer.VERTEX_PRECISION

        self.layer_view.set_model_mesh(glmesh.LayerMesh(segments, self.model.bounding_box))
        self.layer_view.view_all()

    def on_settings(self, event):
        with settingsdialog.SettingsDialog(self) as dialog:
            dialog.set_build_volume(self.settings.build_volume)

            if dialog.ShowModal() != wx.ID_CANCEL:
                build_volume = dialog.get_build_volume()
                self.settings.build_volume = build_volume

                self.model_view.platform_mesh.set_dimensions(build_volume)
                self.Refresh()

    def on_size(self, event):
        if self.IsMaximized():
            self.settings.app_window_maximized = True
        else:
            self.settings.app_window_maximized = False
            self.settings.app_window_size = self.GetSize()

        event.Skip()

    def on_close(self, event):
        try:
            self.settings.save()
        except IOError:
            pass

        # Application does not close if window is minimized
        if self.IsIconized():
            self.Restore()

        self.Destroy()


if __name__ == "__main__":
    # https://docs.microsoft.com/en-us/windows/desktop/api/Winuser/nf-winuser-setthreaddpiawarenesscontext
    ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)

    # https://github.com/prusa3d/PrusaSlicer/blob/563a1a8441dbb7586a167c4bdce0e083e3774980/src/slic3r/GUI/GUI_Utils.hpp#L39
    # https://github.com/prusa3d/PrusaSlicer/blob/eebb9e3fe79cbda736bf95349c5c403ec4aef184/src/slic3r/GUI/GUI_App.cpp#L90
    # https://github.com/prusa3d/PrusaSlicer/blob/563a1a8441dbb7586a167c4bdce0e083e3774980/src/slic3r/GUI/GUI_Utils.hpp#L55

    app = wx.App()
    frame = MainFrame()
    frame.Show()
    app.MainLoop()
