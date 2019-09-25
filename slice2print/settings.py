import copy
import json
import os.path
import sys

import slicer

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
        "nozzle_diameter": 0.4,
        "filament_diameter": 1.75
    },
    "print_options": {
        "first_layer_height": 0.2,
        "layer_height": 0.2,
        "first_layer_speed": 35,
        "print_speed": 50,
        "travel_speed": 150,  # This value does not really change once set, so is it maybe a printer setting?
        "perimeters": 2,
        "top_layers": 4,
        "bottom_layers": 4
    }
}


class Settings:
    APP_NAME = "Slice2Print"
    FILE_NAME = "settings.json"

    def __init__(self):
        if sys.platform == "win32":
            # https://blogs.msdn.microsoft.com/patricka/2010/03/18/where-should-i-store-my-data-and-configuration-files-if-i-target-multiple-os-versions/
            self.path_to_folder = os.path.expandvars("%APPDATA%")
        elif sys.platform.startswith("linux"):
            # https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
            if os.getenv("XDG_CONFIG_HOME") is not None:
                self.path_to_folder = os.path.expandvars("$XDG_CONFIG_HOME")
            else:
                self.path_to_folder = os.path.expanduser("~/.config/")
        else:
            raise RuntimeError(f"Unsupported platform: {sys.platform}")

        self.path_to_folder = os.path.join(self.path_to_folder, self.APP_NAME)
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

                    # TODO Join DEFAULT_SETTINGS and settings from file in a way that missing entries will be added
                    # TODO Check data types during joining
                    self.settings = {**DEFAULT_SETTINGS, **s}  # https://www.python.org/dev/peps/pep-0448/
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

    def get_slicer_config(self):
        cfg = slicer.SlicerConfig()
        cfg.first_layer_height = self.first_layer_height
        cfg.layer_height = self.layer_height
        cfg.nozzle_diameter = self.nozzle_diameter
        cfg.filament_diameter = self.filament_diameter
        cfg.first_layer_speed = self.first_layer_speed
        cfg.print_speed = self.print_speed
        cfg.travel_speed = self.travel_speed
        cfg.perimeters = self.perimeters
        cfg.top_layers = self.top_layers
        cfg.bottom_layers = self.bottom_layers

        return cfg

    @property
    def build_volume(self):
        """
        Falls back to default values in case of an error
        :return: Build volume dimensions as tuple (x, y, z)
        """
        build_volume = self.settings["printer"]["build_volume"]

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
        return self.settings["application"]["window"]["maximized"]

    @app_window_maximized.setter
    def app_window_maximized(self, maximized):
        """
        :param maximized: True if application window is maximized else False
        """
        self.settings["application"]["window"]["maximized"] = maximized

    @property
    def first_layer_height(self):
        return self.settings["print_options"]["first_layer_height"]

    @first_layer_height.setter
    def first_layer_height(self, h):
        self.settings["print_options"]["first_layer_height"] = h

    @property
    def layer_height(self):
        return self.settings["print_options"]["layer_height"]

    @layer_height.setter
    def layer_height(self, h):
        self.settings["print_options"]["layer_height"] = h

    @property
    def nozzle_diameter(self):
        return self.settings["printer"]["nozzle_diameter"]

    @nozzle_diameter.setter
    def nozzle_diameter(self, d):
        self.settings["printer"]["nozzle_diameter"] = d

    @property
    def first_layer_speed(self):
        return self.settings["print_options"]["first_layer_speed"]

    @first_layer_speed.setter
    def first_layer_speed(self, s):
        self.settings["print_options"]["first_layer_speed"] = s

    @property
    def print_speed(self):
        return self.settings["print_options"]["print_speed"]

    @print_speed.setter
    def print_speed(self, s):
        self.settings["print_options"]["print_speed"] = s

    @property
    def travel_speed(self):
        return self.settings["print_options"]["travel_speed"]

    @travel_speed.setter
    def travel_speed(self, s):
        self.settings["print_options"]["travel_speed"] = s

    @property
    def filament_diameter(self):
        return self.settings["printer"]["filament_diameter"]

    @filament_diameter.setter
    def filament_diameter(self, d):
        self.settings["printer"]["filament_diameter"] = d

    @property
    def perimeters(self):
        return self.settings["print_options"]["perimeters"]

    @perimeters.setter
    def perimeters(self, p):
        self.settings["print_options"]["perimeters"] = p

    @property
    def top_layers(self):
        return self.settings["print_options"]["top_layers"]

    @top_layers.setter
    def top_layers(self, layers):
        self.settings["print_options"]["top_layers"] = layers

    @property
    def bottom_layers(self):
        return self.settings["print_options"]["bottom_layers"]

    @bottom_layers.setter
    def bottom_layers(self, layers):
        self.settings["print_options"]["bottom_layers"] = layers
