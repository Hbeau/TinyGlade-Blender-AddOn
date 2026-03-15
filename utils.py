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


def apply_edge_split(context: bpy.types.Context, obj: "bpy.types.Object"):
    """Create a temporary object with edge split modifier applied and return evaluated mesh.
    
    Returns (temp_obj, obj_eval, eval_mesh) where temp_obj is the temporary object,
    obj_eval is the evaluated object, and eval_mesh is the evaluated mesh.
    The caller is responsible for cleaning up temp_obj and obj_eval.
    """
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
    
    return temp_obj, obj_eval, eval_mesh


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
    if obj is None or obj.type != 'MESH':
        raise ValueError("Object must be a mesh object")
    
    temp_obj, obj_eval, eval_mesh = apply_edge_split(context, obj)
    
    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(eval_mesh)   # fill it in from a Mesh

    # Créer une liste pour stocker les positions des vertices
    verts_positions = []

    # Parcourir toutes les faces et ajouter un vertex au centre de chaque face
    for vert in bm.verts:
        for face in vert.link_faces:
            center = face.calc_center_median()
            verts_positions.append(center)
            break

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
    
    return temp_mesh


def vertex_positions_data(obj: "bpy.types.Object", mesh: "bpy.types.Mesh"):
    """Return a list of oriented vertex position tuples for export.

    Applies the object's world matrix before flipping coordinate orientation.
    """
    vertices = [Vector(obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
    return [tuple(flip_vector_orientation(v)) for v in vertices]


def vertex_normals_data(mesh: "bpy.types.Mesh"):
    """Return a list of oriented vertex normal tuples."""
    return [tuple(flip_vector_orientation(v.normal)) for v in mesh.vertices]


def faces_indices_data(mesh: "bpy.types.Mesh"):
    """Return a flat list of triangle indices from a triangulated mesh."""
    faces = []
    for poly in mesh.polygons:
        tri = [poly.vertices[0], poly.vertices[2], poly.vertices[1]]
        faces.extend(tri)
    return faces
    