import wx

from ui import PrintOptionsPanel, PrinterSettingsPanel, modelview


class MainFrameFileDropTarget(wx.FileDropTarget):
    def __init__(self, file_drop_callback):
        wx.FileDropTarget.__init__(self)
        self.file_drop_callback = file_drop_callback

    def OnDropFiles(self, x, y, filenames):
        self.file_drop_callback(filenames)
        return True

    def OnDragOver(self, x, y, d):
        return wx.DragMove


class MainFrame(wx.Frame):
    ACCEL_EXIT = wx.NewIdRef()

    def __init__(self, controller, settings_):
        self.settings = settings_
        self.controller = controller

        wx.Frame.__init__(self, None, title="Slice2Print", size=self.settings.app_window_size)

        self.SetMinSize((640, 480))

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

    def on_exit(self, event):
        self.Close()

    def on_size(self, event):
        self.controller.frame_size_changed()
        event.Skip()

    def on_close(self, event):
        self.controller.close_frame()
