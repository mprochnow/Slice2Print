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

import wx

import glview
import icons
import model
import settings
import settingsdialog


class MainFrame(wx.Frame):
    ACCEL_EXIT = wx.NewIdRef()

    def __init__(self):
        self.settings = settings.Settings()
        self.settings.load_from_file()

        wx.Frame.__init__(self, None, title="Slice2Print", size=(800, 600))
        self.toolbar = self.CreateToolBar()
        self.tool_open = self.toolbar.AddTool(wx.ID_ANY, "", icons.folder.GetBitmap(), shortHelp="Open")
        self.toolbar.AddSeparator()
        self.tool_settings = self.toolbar.AddTool(wx.ID_ANY, "", icons.wrench_orange.GetBitmap(), shortHelp="Settings")
        self.toolbar.Realize()

        self.canvas = glview.GlCanvas(self)

        self.Bind(wx.EVT_MENU, self.on_exit, id=MainFrame.ACCEL_EXIT)
        self.Bind(wx.EVT_TOOL, self.on_open, id=self.tool_open.GetId())
        self.Bind(wx.EVT_TOOL, self.on_settings, id=self.tool_settings.GetId())
        self.Bind(wx.EVT_CLOSE, self.on_close)

        self.SetAcceleratorTable(
            wx.AcceleratorTable([wx.AcceleratorEntry(wx.ACCEL_NORMAL, wx.WXK_ESCAPE, MainFrame.ACCEL_EXIT),
                                 wx.AcceleratorEntry(wx.ACCEL_CTRL, ord("O"), self.tool_open.GetId())]))

    def on_exit(self, event):
        self.Close()

    def on_open(self, event):
        with wx.FileDialog(self, "Open model", wildcard="3D model (*.stl)|*.stl|All files (*.*)|*.*",
                           style=wx.FD_FILE_MUST_EXIST) as dialog:
            if dialog.ShowModal() != wx.ID_CANCEL:
                parser = model.StlAsciiFileParser(dialog.GetPath())
                try:
                    vertices, normals, indices, bb = parser.parse()
                    self.canvas.create_mesh(vertices, normals, indices, bb)

                except (AssertionError, ValueError) as e:
                    msg = "Error in line %s of %s: %s" % (parser.ln_no, parser.filename, e)

    def on_settings(self, event):
        with settingsdialog.SettingsDialogA(self) as dialog:
            dialog.set_build_volume(self.settings.build_volume)

            if dialog.ShowModal() != wx.ID_CANCEL:
                self.settings.build_volume = dialog.get_build_volume()

    def on_close(self, event):
        try:
            self.settings.save()
        except IOError:
            pass

        event.Skip()


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
