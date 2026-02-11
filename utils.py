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

from mathutils import Vector
import bpy
import bmesh


def flip_vector_orientation(vector: Vector) -> Vector:
    """Convert a vector from Tiny Glade coordinates to Blender coordinates."""
    return Vector((-vector.x, vector.z, vector.y))

def pre_export_pipeline(context: bpy.types.Context, obj: "bpy.types.Object"):
    """Create a non-destructive evaluated, triangulated mesh for export.

    Applies modifiers (including edge split) to a single object, converts color 
    attributes to vertex colors, and triangulates.

    Returns (temp_mesh, meta) where `temp_mesh` is a new bpy.data.meshes entry
    containing the evaluated and triangulated geometry, and `meta` is 
    a dict with mapping helpers (currently includes `loop_to_vertex_map`).

    This function always applies modifiers and triangulates.
    The caller is responsible for removing `temp_mesh` from `bpy.data.meshes`.
    """
    depsgraph = context.evaluated_depsgraph_get()
    
    if obj is None or obj.type != 'MESH':
        raise ValueError("Object must be a mesh object")
    
    # Create a temporary copy of the object for non-destructive processing
    temp_obj = obj.copy()
    temp_obj.data = obj.data.copy()
    bpy.context.collection.objects.link(temp_obj)
    
    # Add edge split modifier to the temporary object
    edge_split = temp_obj.modifiers.new(name="EdgeSplit", type='EDGE_SPLIT')
    edge_split.use_edge_angle = True
    edge_split.split_angle = 0.5236  # ~30 degrees in radians
    
    # Update depsgraph to include new modifiers
    depsgraph = context.evaluated_depsgraph_get()
    
    # Get evaluated object with modifiers applied (including edge split)
    obj_eval = temp_obj.evaluated_get(depsgraph)
    
    # Get evaluated mesh with modifiers applied
    try:
        eval_mesh = obj_eval.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)
    except TypeError:
        try:
            eval_mesh = obj_eval.to_mesh()
        except Exception:
            eval_mesh = temp_obj.data.copy()
    
    # Convert color attributes from CORNER to per-vertex format
    if eval_mesh.color_attributes:
        for color_attr in eval_mesh.color_attributes:
            if color_attr.domain == 'CORNER':
                # Create new per-vertex color attribute
                vertex_color = eval_mesh.color_attributes.new(
                    name=color_attr.name + "_vertex",
                    type='FLOAT_COLOR',
                    domain='POINT'
                )
                
                # Map corner colors to first-seen per-vertex
                for loop_idx, loop in enumerate(eval_mesh.loops):
                    v_idx = loop.vertex_index
                    corner_color = color_attr.data[loop_idx].color
                    # Only set if not already set (first-seen)
                    if all(vertex_color.data[v_idx].color[i] == 0.0 for i in range(4)):
                        vertex_color.data[v_idx].color = corner_color
    
    # Triangulate the mesh
    bm = bmesh.new()
    bm.from_mesh(eval_mesh)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    
    # Create final output mesh (unlinked)
    temp_mesh = bpy.data.meshes.new(obj.name + "_tg_export")
    bm.to_mesh(temp_mesh)
    bm.free()
    
    # Clean up temporary object and its data
    if hasattr(obj_eval, "to_mesh_clear"):
        try:
            obj_eval.to_mesh_clear()
        except Exception:
            pass
    
    bpy.data.objects.remove(temp_obj)
    
    # Build simple metadata: loop -> vertex map for first-seen mapping
    loop_to_vertex_map = [loop.vertex_index for loop in temp_mesh.loops]
    meta = {"loop_to_vertex_map": loop_to_vertex_map}
    
    return temp_mesh, meta
    