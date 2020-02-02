import wx


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
