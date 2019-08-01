import copy
import json
import os.path
import sys

DEFAULT_SETTINGS = {
    "application": {
        "window": {
            "width": 800,
            "height": 600,
            "maximized": False
        }
    },
    "printer": {
        "build_volume": {
            "x": 200,
            "y": 200,
            "z": 200
        },
        "nozzle_diameter": 0.4
    },
    "print_options": {
        "first_layer_height": 0.2,
        "layer_height": 0.2
    }
}


class Settings:
    APP_NAME = "Slice2Print"
    FILE_NAME = "settings.json"

    def __init__(self):
        if sys.platform == "win32":
            # https://blogs.msdn.microsoft.com/patricka/2010/03/18/where-should-i-store-my-data-and-configuration-files-if-i-target-multiple-os-versions/
            self.path_to_folder = os.path.expandvars("%%APPDATA%%\\%s\\" % self.APP_NAME)
        elif sys.platform.startswith("linux"):
            # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
            if os.getenv("XDG_CONFIG_HOME") is not None:
                self.path_to_folder = os.path.expandvars("$XDG_CONFIG_HOME/%s/" % self.APP_NAME)
            else:
                self.path_to_folder = os.path.expanduser("~/.config/")
        else:
            raise RuntimeError("Unsupported platform: %s" % sys.platform)

        self.path_to_file = os.path.join(self.path_to_folder, self.FILE_NAME)
        self.settings = copy.deepcopy(DEFAULT_SETTINGS)

    def load_from_file(self):
        """
        Loads settings from JSON file. Falls back to default values in case of an error.
        """
        try:
            with open(self.path_to_file, "r") as f:
                try:
                    s = json.load(f)
                    self.settings = {**DEFAULT_SETTINGS, **s}  # https://www.python.org/dev/peps/pep-0448/

                    print(json.dumps(self.settings, indent=4))
                except json.JSONDecodeError:
                    pass
        except IOError:
            pass

    def save(self):
        """
        Saves settings to JSON file.
        :raises IOError:
        """
        if not os.path.isdir(self.path_to_folder):
            os.mkdir(self.path_to_folder)

        with open(self.path_to_file, "w") as f:
            json.dump(self.settings, f, indent=2, sort_keys=True)

    @property
    def build_volume(self):
        """
        Falls back to default values in case of an error
        :return: Build volume dimensions as tuple (x, y, z)
        """
        build_volume = self.settings["printer"]["build_volume"]

        try:
            assert isinstance(build_volume["x"], (int, float)) and \
                isinstance(build_volume["y"], (int, float)) and \
                isinstance(build_volume["z"], (int, float))

            assert build_volume["x"] > 0 and build_volume["y"] > 0 and build_volume["z"] > 0
        except AssertionError:
            build_volume = DEFAULT_SETTINGS["printer"]["build_volume"]

        return build_volume["x"], build_volume["y"], build_volume["z"]

    @build_volume.setter
    def build_volume(self, dimensions):
        """
        :param dimensions: Build volume dimensions as tuple (x, y, z)
        """
        build_volume = self.settings["printer"]["build_volume"]

        build_volume["x"] = dimensions[0]
        build_volume["y"] = dimensions[1]
        build_volume["z"] = dimensions[2]

    @property
    def app_window_size(self):
        """
        :return: Application window size as tuple (width, height)
        """
        window = self.settings["application"]["window"]

        try:
            assert isinstance(window["width"], int) and isinstance(window["height"], int)
            assert window["width"] > 0 and window["height"] > 0
        except AssertionError:
            window["width"] = DEFAULT_SETTINGS["application"]["window"]["width"]
            window["height"] = DEFAULT_SETTINGS["application"]["windows"]["height"]

        return window["width"], window["height"]

    @app_window_size.setter
    def app_window_size(self, size):
        """
        :param size: Application window size as tuple (width, height)
        """
        window = self.settings["application"]["window"]

        window["width"], window["height"] = size

    @property
    def app_window_maximized(self):
        """
        :return: True if application window shall be maximized else False
        """
        window = self.settings["application"]["window"]

        try:
            assert isinstance(window["maximized"], bool)
        except AssertionError:
            window["maximized"] = DEFAULT_SETTINGS["application"]["window"]["maximized"]

        return window["maximized"]

    @app_window_maximized.setter
    def app_window_maximized(self, maximized):
        """
        :param maximized: True if application window is maximized else False
        """
        self.settings["application"]["window"]["maximized"] = maximized

    @property
    def first_layer_height(self):
        try:
            assert isinstance(self.settings["print_options"]["first_layer_height"], float)
        except AssertionError:
            self.settings["print_options"]["first_layer_height"] = \
                DEFAULT_SETTINGS["print_options"]["first_layer_height"]

        return self.settings["print_options"]["first_layer_height"]

    @first_layer_height.setter
    def first_layer_height(self, h):
        self.settings["print_options"]["first_layer_height"] = h

    @property
    def layer_height(self):
        try:
            assert isinstance(self.settings["print_options"]["layer_height"], float)
        except AssertionError:
            self.settings["print_options"]["layer_height"] = DEFAULT_SETTINGS["print_options"]["layer_height"]

        return self.settings["print_options"]["layer_height"]

    @layer_height.setter
    def layer_height(self, h):
        self.settings["print_options"]["layer_height"] = h

    @property
    def nozzle_diameter(self):
        try:
            assert isinstance(self.settings["printer"]["nozzle_diameter"], float)
        except AssertionError:
            self.settings["printer"]["nozzle_diameter"] = DEFAULT_SETTINGS["printer"]["nozzle_diameter"]

        return self.settings["printer"]["nozzle_diameter"]

    @nozzle_diameter.setter
    def nozzle_diameter(self, d):
        self.settings["printer"]["nozzle_diameter"] = d
