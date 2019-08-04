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


class SlicerConfig:
    def __init__(self):
        self.first_layer_height = None
        self.layer_height = None

        self.nozzle_diameter = None
        self.filament_diameter = None

        self.first_layer_speed = None
        self.print_speed = None
        self.travel_speed = None

        self.perimeters = None

    @property
    def extrusion_width(self):
        return self.nozzle_diameter * 1.2
