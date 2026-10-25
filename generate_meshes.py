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


# Generate Appear Pos Mesh Operator
class GenerateAppearPosMesh(bpy.types.Operator):
    """Generate a mesh with the selected mesh's vertex positions"""
    bl_idname = "mesh.generate_appear_pos_mesh"
    bl_label = "Generate Appear Pos Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        temp_obj, obj_eval, eval_mesh = apply_edge_split(context, obj)
        appear_pos = [(v.co.x, v.co.y, v.co.z) for v in eval_mesh.vertices]

        
        # Clean up temporary object and its data
        if hasattr(obj_eval, "to_mesh_clear"):
            try:
                obj_eval.to_mesh_clear()
            except Exception:
                pass
        
        bpy.data.objects.remove(temp_obj)
        # Create new mesh and object for appear_pos
        appear_mesh = bpy.data.meshes.new("AppearPosMesh")
        appear_mesh.from_pydata(appear_pos, [], [])
        appear_obj = bpy.data.objects.new("AppearPosObject", appear_mesh)
        bpy.context.collection.objects.link(appear_obj)
        appear_mesh.update()
        
        self.report({'INFO'}, "Generated Appear Pos Mesh")
        return {'FINISHED'}


# Generate Prim Center Mesh Operator
class GeneratePrimCenterMesh(bpy.types.Operator):
    """Generate a mesh with each vertex at the center of one of its linked faces"""
    bl_idname = "mesh.generate_prim_center_mesh"
    bl_label = "Generate Prim Center Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        temp_obj, obj_eval, eval_mesh = apply_edge_split(context, obj)

        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        prim_center = [None] * len(bm.verts)
        for vert in bm.verts:
            center = vert.link_faces[0].calc_center_median() if vert.link_faces else vert.co
            prim_center[vert.index] = (center.x, center.y, center.z)
        bm.free()
        
        # Clean up temporary object and its data
        if hasattr(obj_eval, "to_mesh_clear"):
            try:
                obj_eval.to_mesh_clear()
            except Exception:
                pass
        
        bpy.data.objects.remove(temp_obj)
        
        # Create new mesh and object for prim_center
        prim_mesh = bpy.data.meshes.new("PrimCenterMesh")
        prim_mesh.from_pydata(prim_center, [], [])
        prim_obj = bpy.data.objects.new("PrimCenterObject", prim_mesh)
        bpy.context.collection.objects.link(prim_obj)
        prim_mesh.update()
        
        self.report({'INFO'}, "Generated Prim Center Mesh")
        return {'FINISHED'}