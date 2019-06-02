import copy
import json
import os.path
import sys


class Settings:
    APP_NAME = "Slice2Print"
    FILE_NAME = "settings.json"

    DEFAULT = {
        "build_volume": {
            "x": 200,
            "y": 200,
            "z": 200
        }
    }

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
        self.settings = copy.deepcopy(self.DEFAULT)

    def load_from_file(self):
        """
        Loads settings from JSON file. Falls back to default values in case of an error.
        """
        try:
            with open(self.path_to_file, "r") as f:
                try:
                    self.settings = json.load(f)
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

        settings = dict()
        settings["build_volume"] = dict()
        settings["build_volume"]["x"], settings["build_volume"]["y"], settings["build_volume"]["z"] = self.build_volume

        with open(self.path_to_file, "w") as f:
            json.dump(settings, f, indent=2, sort_keys=True)

    @property
    def build_volume(self):
        """
        Falls back to default values in case of an error
        :return: Build volume dimensions as tuple (x, y, z)
        """
        try:
            build_volume = self.settings["build_volume"]

            assert isinstance(build_volume["x"], (int, float)) and \
                isinstance(build_volume["y"], (int, float)) and \
                isinstance(build_volume["z"], (int, float))

            assert build_volume["x"] > 0 and build_volume["y"] > 0 and build_volume["z"] > 0

            return build_volume["x"], build_volume["y"], build_volume["z"]
        except (AssertionError, KeyError) as e:
            build_volume = self.DEFAULT["build_volume"]
            return build_volume["x"], build_volume["y"], build_volume["z"]

    @build_volume.setter
    def build_volume(self, dimensions):
        """
        :param dimensions: Build volume dimensions as tuple (x, y, z)
        """
        build_volume = self.settings["build_volume"]
        build_volume["x"] = dimensions[0]
        build_volume["y"] = dimensions[1]
        build_volume["z"] = dimensions[2]
