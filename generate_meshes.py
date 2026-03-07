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
    """Generate a mesh with vertices at appear positions from the selected mesh"""
    bl_idname = "mesh.generate_appear_pos_mesh"
    bl_label = "Generate Appear Pos Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        temp_obj, obj_eval, eval_mesh = apply_edge_split(context, obj)
        
        # Compute appear_pos: per vertex, center of first linked face
        appear_pos = [None] * len(eval_mesh.vertices)
        bm = bmesh.new()
        bm.from_mesh(eval_mesh)
        print("Generating appear_pos mesh from evaluated mesh with", len(bm.verts), "vertices")
        for vert in bm.verts:
            if vert.link_faces is None or len(vert.link_faces) == 0:
                print(f"Vertex {vert.index} has no linked faces, using vertex position as appear_pos")
                center = vert.co
                appear_pos[vert.index] = (center.x, center.y, center.z)
            else:
                for face in vert.link_faces:
                    print(f"Processing vertex {vert.index} with linked face {face.index}")
                    if face is None:
                        center = vert.co
                        appear_pos[vert.index] = (center.x, center.y, center.z)
                    else:
                        center = face.calc_center_median()
                    appear_pos[vert.index] = (center.x, center.y, center.z)
                    break
        bm.free()

        
        # Clean up temporary object and its data
        if hasattr(obj_eval, "to_mesh_clear"):
            try:
                obj_eval.to_mesh_clear()
            except Exception:
                pass
        
        bpy.data.objects.remove(temp_obj)
        print("appear_pos data:", appear_pos)
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
    """Generate a mesh with vertices duplicating the vertex positions of the selected mesh (after modifiers)"""
    bl_idname = "mesh.generate_prim_center_mesh"
    bl_label = "Generate Prim Center Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        
        temp_obj, obj_eval, eval_mesh = apply_edge_split(context, obj)
        
        # Get vertex positions (local, without world matrix or flip, as they will be exported without transformation)
        vertex_positions = [(v.co.x, v.co.y, v.co.z) for v in eval_mesh.vertices]
        
        # Clean up temporary object and its data
        if hasattr(obj_eval, "to_mesh_clear"):
            try:
                obj_eval.to_mesh_clear()
            except Exception:
                pass
        
        bpy.data.objects.remove(temp_obj)
        
        # Create new mesh and object for prim_center
        prim_mesh = bpy.data.meshes.new("PrimCenterMesh")
        prim_mesh.from_pydata(vertex_positions, [], [])
        prim_obj = bpy.data.objects.new("PrimCenterObject", prim_mesh)
        bpy.context.collection.objects.link(prim_obj)
        prim_mesh.update()
        
        self.report({'INFO'}, "Generated Prim Center Mesh")
        return {'FINISHED'}