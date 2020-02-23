import wx
from ui import icons


class MainFrameToolBar(wx.ToolBar):
    def __init__(self, frame, controller):
        wx.ToolBar.__init__(self, frame, style=wx.TB_DEFAULT_STYLE)
        self.frame = frame
        self.controller = controller
        self.tool_slice = None
        self.tool_model_view = None
        self.tool_layer_view = None
        self.tool_view_all = None
        self.tool_view_from_top = None

        self._create_tools()

    def enable_model_tools(self, enable=True):
        self.EnableTool(self.tool_slice.GetId(), enable)
        self.EnableTool(self.tool_view_all.GetId(), enable)
        self.EnableTool(self.tool_view_from_top.GetId(), enable)

    def enable_layer_view_tool(self, enable=True):
        self.EnableTool(self.tool_layer_view.GetId(), enable)
        self.EnableTool(self.tool_svg.GetId(), enable)

    def toggle_model_view(self):
        self.EnableTool(self.tool_svg.GetId(), False)
        self.ToggleTool(self.tool_model_view.GetId(), True)

    def toggle_layer_view(self):
        self.EnableTool(self.tool_svg.GetId(), True)
        self.ToggleTool(self.tool_layer_view.GetId(), True)

    def _create_tools(self):
        tool_open = self.AddTool(wx.ID_ANY, "Load model", icons.plussquare24.GetBitmap(), shortHelp="Load model")

        self.AddSeparator()

        self.tool_slice = self.AddTool(wx.ID_ANY,
                                       "Slice model",
                                       icons.play24.GetBitmap(),
                                       icons.play24_disabled.GetBitmap(),
                                       shortHelp="Slice model")

        self.AddSeparator()

        self.tool_model_view = self.AddRadioTool(wx.ID_ANY,
                                                 "Model view",
                                                 icons.box24.GetBitmap(),
                                                 icons.box24_disabled.GetBitmap(),
                                                 shortHelp="Model view")

        self.tool_layer_view = self.AddRadioTool(wx.ID_ANY,
                                                 "Layer view",
                                                 icons.boxsliced24.GetBitmap(),
                                                 icons.boxsliced24_disabled.GetBitmap(),
                                                 shortHelp="Layer view")

        self.AddSeparator()

        self.tool_view_all = self.AddTool(wx.ID_ANY,
                                          "View all",
                                          icons.maximize24.GetBitmap(),
                                          icons.maximize24_disabled.GetBitmap(),
                                          shortHelp="View all")

        self.tool_view_from_top = self.AddTool(wx.ID_ANY,
                                               "View from top",
                                               icons.boxtop24.GetBitmap(),
                                               icons.boxtop24_disabled.GetBitmap(),
                                               shortHelp="View from top")

        self.AddSeparator()

        self.tool_svg = self.AddTool(wx.ID_ANY,
                                     "Layer outline to SVG",
                                     icons.image24.GetBitmap(),
                                     icons.image24_disabled.GetBitmap(),
                                     shortHelp="Layer outline to SVG")

        self.Realize()

        self.frame.Bind(wx.EVT_TOOL, self.controller.load_model, id=tool_open.GetId())
        self.frame.Bind(wx.EVT_TOOL, self.controller.view_all, id=self.tool_view_all.GetId())
        self.frame.Bind(wx.EVT_TOOL, self.controller.slice_model, id=self.tool_slice.GetId())
        self.frame.Bind(wx.EVT_TOOL, self.controller.show_model_mesh, id=self.tool_model_view.GetId())
        self.frame.Bind(wx.EVT_TOOL, self.controller.show_layer_mesh, id=self.tool_layer_view.GetId())
        self.frame.Bind(wx.EVT_TOOL, self.controller.view_from_top, id=self.tool_view_from_top.GetId())
        self.frame.Bind(wx.EVT_TOOL, self.controller.layer_to_svg, id=self.tool_svg.GetId())

        self.enable_model_tools(False)
        self.enable_layer_view_tool(False)
