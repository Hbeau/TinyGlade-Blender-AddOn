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

from . import operators
from . import overlay

def menu_func_vertex(self, context):
    self.layout.operator(operators.ToggleMetalAttribute.bl_idname, text="Toggle Metal")
    self.layout.operator(operators.ToggleGlassAttribute.bl_idname, text="Toggle Glass")

def menu_func_import(self, context):
    self.layout.operator(operators.ImportTinyGladeJSON.bl_idname, text="Tiny Glade JSON (.json)")

def menu_func_export(self, context):
    self.layout.operator(operators.ExportTinyGladeJSON.bl_idname, text="Tiny Glade JSON (.json)")

# Register the add-on
def register():
    bpy.types.Scene.show_material_overlay = bpy.props.BoolProperty(
        name="Material Attributes",
        description="Show material attributes overlay on active mesh",
        default=False,
        update=overlay.update_show_overlay_scene
    )
    bpy.utils.register_class(operators.ImportTinyGladeJSON)
    bpy.utils.register_class(operators.ExportTinyGladeJSON)
    #bpy.utils.register_class(operators.VisualizeMaterialAttributes)
    bpy.utils.register_class(operators.ToggleMetalAttribute)
    bpy.utils.register_class(operators.ToggleGlassAttribute)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.VIEW3D_PT_overlay_edit_mesh.append(overlay.overlay_panel_draw)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func_vertex)

def unregister():
    # Remove draw handlers
    try:
        for area in bpy.context.screen.areas:
            if area.type == 'VIEW_3D':
                space = area.spaces[0]
                try:
                    if hasattr(space, 'material_overlay_handler'):
                        space.draw_handler_remove(space.material_overlay_handler, 'WINDOW')
                        del space.material_overlay_handler
                except AttributeError:
                    pass
    except:
        pass
    bpy.types.VIEW3D_PT_overlay_edit_mesh.remove(overlay.overlay_panel_draw)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func_vertex)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(operators.ImportTinyGladeJSON)
    bpy.utils.unregister_class(operators.ExportTinyGladeJSON)
    #bpy.utils.unregister_class(operators.VisualizeMaterialAttributes)
    bpy.utils.unregister_class(operators.ToggleMetalAttribute)
    bpy.utils.unregister_class(operators.ToggleGlassAttribute)
    del bpy.types.Scene.show_material_overlay
