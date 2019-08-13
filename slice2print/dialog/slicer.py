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

import threading

import wx

import slicer


class SlicerDialog(wx.Dialog):
    def __init__(self, parent, model, slicer_config):
        wx.Dialog.__init__(self, parent, -1, "Slicing...", style=wx.CAPTION)

        self.slicer = None
        self.thread = None
        self.cancel = False
        self.model = model
        self.slicer_config = slicer_config
        self.update_interval = model.facet_count // 100 if model.facet_count > 100 else model.facet_count

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.staticText = wx.StaticText(self, -1, "")
        sizer.Add(self.staticText, 0, wx.EXPAND | wx.ALL, 7)

        self.gauge = wx.Gauge(self, -1, 100)
        self.gauge.SetValue(0)
        sizer.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 7)

        btn_sizer = wx.BoxSizer(wx.VERTICAL)
        btn_cancel = wx.Button(self, 1, "Cancel")
        btn_sizer.Add(btn_cancel, 0, wx.ALIGN_RIGHT)

        sizer.Add(btn_sizer, 0, wx.EXPAND | wx.ALL, 7)

        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=btn_cancel.GetId())

        self.SetSizer(sizer)
        self.Layout()
        self.Fit()
        self.SetSize((400, -1))
        self.CenterOnParent(wx.BOTH)

    def on_cancel(self, event):
        self.cancel = True

    def slice_model(self):
        self.slicer = slicer.ModelSlicer(self.slicer_config, self.model, self.update)
        self.thread = threading.Thread(target=self.slicer.execute)
        self.thread.start()

        return self.ShowModal()

    def get_sliced_model(self):
        return self.slicer.get_sliced_model_outlines()

    def update(self, progress, msg):
        wx.CallAfter(self._update, progress, msg)
        return self.cancel

    def _update(self, progress, msg):
        self.gauge.SetValue(progress)
        self.staticText.SetLabel(msg)

        self.thread.join(0.02)
        if not self.thread.is_alive():
            self.EndModal(wx.ID_CANCEL if self.slicer.cancelled() else wx.ID_OK)
