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


class SettingsDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, title="Settings", size=wx.DefaultSize)

        top_sizer = wx.BoxSizer(wx.VERTICAL)
        bv_sizer = wx.StaticBoxSizer(wx.StaticBox(self, -1, "Build volume"), wx.HORIZONTAL)
        btn_sizer = self.CreateButtonSizer(wx.OK | wx.CANCEL)

        self.ctrl_bv_x = wx.lib.masked.numctrl.NumCtrl(bv_sizer.GetStaticBox(), -1)
        self.ctrl_bv_x.SetAllowNegative(False)
        self.ctrl_bv_x.SetBounds(1, None)
        self.ctrl_bv_x.SetLimited(True)
        bv_sizer.Add(self.ctrl_bv_x, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        bv_sizer.Add(wx.StaticText(bv_sizer.GetStaticBox(), -1, "x"), 0, wx.ALIGN_CENTER_VERTICAL)

        self.ctrl_bv_y = wx.lib.masked.numctrl.NumCtrl(bv_sizer.GetStaticBox(), -1)
        self.ctrl_bv_y.SetAllowNegative(False)
        self.ctrl_bv_y.SetBounds(1, None)
        self.ctrl_bv_y.SetLimited(True)
        bv_sizer.Add(self.ctrl_bv_y, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        bv_sizer.Add(wx.StaticText(bv_sizer.GetStaticBox(), -1, "x"), 0, wx.ALIGN_CENTER_VERTICAL)

        self.ctrl_bv_z = wx.lib.masked.numctrl.NumCtrl(bv_sizer.GetStaticBox(), -1)
        self.ctrl_bv_z.SetAllowNegative(False)
        self.ctrl_bv_z.SetBounds(1, None)
        self.ctrl_bv_z.SetLimited(True)
        bv_sizer.Add(self.ctrl_bv_z, 1, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 7)

        bv_sizer.Add(wx.StaticText(bv_sizer.GetStaticBox(), -1, "mm"), 0, wx.ALIGN_CENTER_VERTICAL)
        top_sizer.Add(bv_sizer, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 5)
        top_sizer.Add(btn_sizer, 0, wx.EXPAND | wx.TOP | wx.BOTTOM, 7)

        self.SetSizer(top_sizer)
        self.Layout()
        self.Fit()

    def set_build_volume(self, dimensions):
        """
        :param dimensions: Build volume dimensions as tuple (x, y, z)
        """
        self.ctrl_bv_x.SetValue(dimensions[0])
        self.ctrl_bv_y.SetValue(dimensions[1])
        self.ctrl_bv_z.SetValue(dimensions[2])

    def get_build_volume(self):
        """
        :return: Build volume dimensions as tuple (x, y, z)
        """
        return self.ctrl_bv_x.GetValue(), self.ctrl_bv_y.GetValue(), self.ctrl_bv_z.GetValue()


if __name__ == "__main__":
    app = wx.App()

    d = SettingsDialog(None)
    d.ShowModal()

