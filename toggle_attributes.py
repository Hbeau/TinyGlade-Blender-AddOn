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
import numpy as np
import bmesh
from .utils import flip_vector_orientation, pre_export_pipeline, vertex_positions_data, vertex_normals_data, faces_indices_data, apply_edge_split


# Toggle Metal Attribute Operator
class ToggleMetalAttribute(bpy.types.Operator):
    """Toggle is_metal_part attribute on selected vertices"""
    bl_idname = "mesh.toggle_metal_attribute"
    bl_label = "Toggle Metal Attribute"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Must be in edit mode")
            return {'CANCELLED'}
        
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        # Get or create the is_metal_part attribute
        metal_attr = mesh.attributes.get('is_metal_part')
        if not metal_attr:
            metal_attr = mesh.attributes.new(name='is_metal_part', type='INT', domain='POINT')
        
        # Toggle for selected vertices
        metal_layer = bm.verts.layers.int.get('is_metal_part')
        for vert in bm.verts:
            if vert.select:
                vert[metal_layer] = 1 if vert[metal_layer] == 0  else 0

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "Toggled metal attribute on selected vertices")
        return {'FINISHED'}


# Toggle Glass Attribute Operator
class ToggleGlassAttribute(bpy.types.Operator):
    """Toggle is_glass attribute on selected vertices"""
    bl_idname = "mesh.toggle_glass_attribute"
    bl_label = "Toggle Glass Attribute"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Must be in edit mode")
            return {'CANCELLED'}
        
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        # Get or create the is_glass attribute
        glass_attr = mesh.attributes.get('is_glass')
        if not glass_attr:
            glass_attr = mesh.attributes.new(name='is_glass', type='INT', domain='POINT')
        
        glass_layer = bm.verts.layers.int.get('is_glass')
        for vert in bm.verts:
            if vert.select:
                vert[glass_layer] = 1 if vert[glass_layer] == 0  else 0

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "Toggled glass attribute on selected vertices")
        return {'FINISHED'}


# Toggle Canopy Attribute Operator
class ToggleCanopyAttribute(bpy.types.Operator):
    """Toggle is_canopy attribute on selected vertices"""
    bl_idname = "mesh.toggle_canopy_attribute"
    bl_label = "Toggle Canopy Attribute"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        if obj.mode != 'EDIT':
            self.report({'ERROR'}, "Must be in edit mode")
            return {'CANCELLED'}
        
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        
        # Get or create the is_canopy attribute
        canopy_attr = mesh.attributes.get('is_canopy')
        if not canopy_attr:
            canopy_attr = mesh.attributes.new(name='is_canopy', type='INT', domain='POINT')
        
        canopy_layer = bm.verts.layers.int.get('is_canopy')
        for vert in bm.verts:
            if vert.select:
                vert[canopy_layer] = 1 if vert[canopy_layer] == 0  else 0

        bmesh.update_edit_mesh(mesh)
        self.report({'INFO'}, "Toggled canopy attribute on selected vertices")
        return {'FINISHED'}