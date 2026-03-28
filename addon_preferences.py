# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import bpy
from bpy.types import AddonPreferences
from pathlib import Path


class TinyGladeAddonPreferences(AddonPreferences):
    """Preferences for Tiny Glade addon"""
    bl_idname = "tiny_glade_blender_addon"
    
    def draw(self, context):
        layout = self.layout
        
        layout.label(text="Tiny Glade Mesh Preset Configuration")
        layout.label(text="Mesh presets are now embedded in the addon.", icon='INFO')
        layout.label(text="No external files required.")
        
        # Optional: Show preset statistics
        try:
            from . import mesh_presets
            manager = mesh_presets.get_preset_manager()
            if manager.loaded:
                layout.separator()
                layout.label(text=f"Loaded {len(manager.presets)} shader presets")
                layout.label(text=f"Supporting {len(manager.mesh_to_preset)} mesh types")
            else:
                layout.label(text="Presets not loaded", icon='ERROR')
        except ImportError:
            layout.label(text="Could not load preset information", icon='ERROR')


def get_addon_preferences():
    """Get addon preferences"""
    prefs = bpy.context.preferences.addons.get("tiny_glade_blender_addon")
    if prefs:
        return prefs.preferences
    return None