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
import wx.lib.masked.numctrl

LABEL_WIDTH = 150


class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, wx.ID_ANY, title="Settings", size=wx.DefaultSize)

        # Build volume
        build_volume_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Build volume"), wx.HORIZONTAL)

        self.ctrl_build_volume_x = wx.lib.masked.numctrl.NumCtrl(build_volume_sizer.GetStaticBox(), wx.ID_ANY)
        self.ctrl_build_volume_x.SetAllowNegative(False)
        self.ctrl_build_volume_x.SetBounds(1, None)
        self.ctrl_build_volume_x.SetLimited(True)
        build_volume_sizer.Add(self.ctrl_build_volume_x, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        build_volume_sizer.Add(
            wx.StaticText(build_volume_sizer.GetStaticBox(), wx.ID_ANY, "x"), 0, wx.ALIGN_CENTER_VERTICAL)

        self.ctrl_build_volume_y = wx.lib.masked.numctrl.NumCtrl(build_volume_sizer.GetStaticBox(), wx.ID_ANY)
        self.ctrl_build_volume_y.SetAllowNegative(False)
        self.ctrl_build_volume_y.SetBounds(1, None)
        self.ctrl_build_volume_y.SetLimited(True)
        build_volume_sizer.Add(self.ctrl_build_volume_y, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        build_volume_sizer.Add(
            wx.StaticText(build_volume_sizer.GetStaticBox(), wx.ID_ANY, "x"), 0, wx.ALIGN_CENTER_VERTICAL)

        self.ctrl_build_volume_z = wx.lib.masked.numctrl.NumCtrl(build_volume_sizer.GetStaticBox(), wx.ID_ANY)
        self.ctrl_build_volume_z.SetAllowNegative(False)
        self.ctrl_build_volume_z.SetBounds(1, None)
        self.ctrl_build_volume_z.SetLimited(True)
        build_volume_sizer.Add(self.ctrl_build_volume_z, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        build_volume_sizer.Add(wx.StaticText(build_volume_sizer.GetStaticBox(), wx.ID_ANY, "mm"),
                               0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 7)

        e_sizer = wx.StaticBoxSizer(wx.StaticBox(self, wx.ID_ANY, "Extruder"), wx.VERTICAL)

        # Nozzle diameter
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(e_sizer.GetStaticBox(), wx.ID_ANY, "Nozzle diameter", size=wx.Size(LABEL_WIDTH, -1)),
                  0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        self.ctrl_nozzle_diameter = wx.lib.masked.numctrl.NumCtrl(e_sizer.GetStaticBox(), wx.ID_ANY)
        self.ctrl_nozzle_diameter.SetAllowNegative(False)
        self.ctrl_nozzle_diameter.SetFractionWidth(2)
        self.ctrl_nozzle_diameter.SetLimited(True)
        sizer.Add(self.ctrl_nozzle_diameter, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP, 7)

        sizer.Add(wx.StaticText(e_sizer.GetStaticBox(), wx.ID_ANY, "mm"), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.RIGHT, 7)

        e_sizer.Add(sizer, 0, wx.EXPAND)

        # Filament diameter
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(wx.StaticText(e_sizer.GetStaticBox(), wx.ID_ANY, "Filament diameter", size=wx.Size(LABEL_WIDTH, -1)),
                  0, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.BOTTOM, 7)

        self.ctrl_filament_diameter = wx.lib.masked.numctrl.NumCtrl(e_sizer.GetStaticBox(), wx.ID_ANY)
        self.ctrl_filament_diameter.SetAllowNegative(False)
        self.ctrl_filament_diameter.SetFractionWidth(2)
        self.ctrl_filament_diameter.SetLimited(True)
        sizer.Add(self.ctrl_filament_diameter, 1, wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.BOTTOM, 7)

        sizer.Add(wx.StaticText(e_sizer.GetStaticBox(), wx.ID_ANY, "mm"), 0,
                  wx.ALIGN_CENTER_VERTICAL | wx.LEFT | wx.TOP | wx.RIGHT | wx.BOTTOM, 7)

        e_sizer.Add(sizer, 0, wx.EXPAND)

        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        top_sizer.Add(build_volume_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        top_sizer.Add(e_sizer, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        top_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 7)

        self.SetSizer(top_sizer)
        self.Layout()
        self.Fit()

    def set_build_volume(self, dimensions):
        """
        :param dimensions: Build volume dimensions as tuple (x, y, z)
        """
        self.ctrl_build_volume_x.SetValue(dimensions[0])
        self.ctrl_build_volume_y.SetValue(dimensions[1])
        self.ctrl_build_volume_z.SetValue(dimensions[2])

    def get_build_volume(self):
        """
        :return: Build volume dimensions as tuple (x, y, z)
        """
        return self.ctrl_build_volume_x.GetValue(), \
            self.ctrl_build_volume_y.GetValue(), \
            self.ctrl_build_volume_z.GetValue()

    def set_nozzle_diameter(self, nozzle_diameter):
        self.ctrl_nozzle_diameter.SetValue(nozzle_diameter)

    def get_nozzle_diameter(self):
        return self.ctrl_nozzle_diameter.GetValue()

    def set_filament_diameter(self, filament_diameter):
        self.ctrl_filament_diameter.SetValue(filament_diameter)

    def get_filament_diameter(self):
        return self.ctrl_filament_diameter.GetValue()


if __name__ == "__main__":
    app = wx.App()

    d = SettingsDialog(None)
    d.ShowModal()

