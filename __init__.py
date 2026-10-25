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

from . import import_operator
from . import export_operator
from . import tree_export_operator
from . import generate_meshes
from . import addon_preferences
from . import mesh_presets
from . import scalar_attributes

def menu_func_vertex(self, context):
    self.layout.operator(generate_meshes.GeneratePrimCenterMesh.bl_idname, text="Generate Prim Center Mesh")
    self.layout.operator(generate_meshes.GenerateAppearPosMesh.bl_idname, text="Generate Appear Pos Mesh")

def menu_func_import(self, context):
    self.layout.operator(import_operator.ImportTinyGladeJSON.bl_idname, text="Tiny Glade JSON (.json)")

def menu_func_export(self, context):
    self.layout.operator(export_operator.ExportTinyGladeJSON.bl_idname, text="Tiny Glade JSON (.json)")
    self.layout.operator(tree_export_operator.ExportTinyGladeTreeJSON.bl_idname, text="Tiny Glade Tree JSON (.json)")


def init_presets():
    """Initialize mesh presets from embedded data"""
    try:
        manager = mesh_presets.get_preset_manager()
        return manager.load()
    except Exception as e:
        print(f"Failed to initialize presets: {e}")
        return False


# Register the add-on
def register():
    # Register addon preferences first
    bpy.utils.register_class(addon_preferences.TinyGladeAddonPreferences)
    bpy.utils.register_class(scalar_attributes.ScalarGroupSelectionItem)
    
    bpy.types.Scene.tiny_glade_selected_mesh = bpy.props.StringProperty(
        name="Selected Mesh",
        description="Currently selected mesh for export",
        default=""
    )
    bpy.utils.register_class(export_operator.EXPORT_PT_MeshListPopover)
    bpy.utils.register_class(export_operator.EXPORT_OT_MeshSearch)
    bpy.utils.register_class(import_operator.ImportTinyGladeJSON)
    bpy.utils.register_class(export_operator.ExportTinyGladeJSON)
    bpy.utils.register_class(tree_export_operator.ExportTinyGladeTreeJSON)
    bpy.utils.register_class(generate_meshes.GenerateAppearPosMesh)
    bpy.utils.register_class(generate_meshes.GeneratePrimCenterMesh)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.VIEW3D_MT_edit_mesh_vertices.append(menu_func_vertex)
    
    # Initialize presets
    init_presets()

def unregister():
    bpy.types.VIEW3D_MT_edit_mesh_vertices.remove(menu_func_vertex)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.utils.unregister_class(export_operator.EXPORT_PT_MeshListPopover)
    bpy.utils.unregister_class(export_operator.EXPORT_OT_MeshSearch)
    bpy.utils.unregister_class(import_operator.ImportTinyGladeJSON)
    bpy.utils.unregister_class(export_operator.ExportTinyGladeJSON)
    bpy.utils.unregister_class(tree_export_operator.ExportTinyGladeTreeJSON)
    bpy.utils.unregister_class(scalar_attributes.ScalarGroupSelectionItem)
    bpy.utils.unregister_class(generate_meshes.GenerateAppearPosMesh)
    bpy.utils.unregister_class(generate_meshes.GeneratePrimCenterMesh)
    bpy.utils.unregister_class(addon_preferences.TinyGladeAddonPreferences)
    del bpy.types.Scene.tiny_glade_selected_mesh
