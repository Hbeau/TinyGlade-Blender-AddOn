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
import json
from mathutils import Vector
from bpy_extras.io_utils import ImportHelper
from .utils import flip_vector_orientation


# Import Operator
class ImportTinyGladeJSON(bpy.types.Operator, ImportHelper):
    """Load a Tiny Glade JSON file"""
    bl_idname = "import_scene.tiny_glade_json"
    bl_label = "Import Tiny Glade JSON"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"

    # allow the user to choose a different import process for trees
    import_type: bpy.props.EnumProperty(
        name="Import Type",
        description="Choose how to interpret the incoming data",
        items=[
            ('MESH', "Normal Mesh", "Treat vertex colors as colors"),
            ('TREE', "Tree", "Interpret vertex color.x/y as UV and z as canopy flag"),
        ],
        default='MESH',
    )

    def execute(self, context):
        # Open and parse the JSON file
        with open(self.filepath, 'r') as f:
            data = json.load(f)
        vertex_positions = np.array([flip_vector_orientation(Vector(v)) for v in data.get("Vertex_Position",{}).get("buffer", [])])
        vertex_normals = np.array([flip_vector_orientation(Vector(v)) for v in data.get("Vertex_Normal",{}).get("buffer", [])])
        vertex_colors = data.get("Vertex_Color",{}).get("buffer", [])
        vertex_UV = data.get("Vertex_UV",{}).get("buffer", [])
        indices = data.get("indices",{}).get("buffer", [])
        faces = [indices[i:i+3] for i in range(0, len(indices), 3)]
        prim_center = np.array([flip_vector_orientation(Vector(v)) for v in data.get("prim_center",{}).get("buffer", [])])
        appear_pos = np.array([flip_vector_orientation(Vector(v)) for v in data.get("appear_pos",{}).get("buffer", [])])
        is_metal = data.get("is_metal_part",{}).get("buffer", [])
        is_glass = data.get("is_glass",{}).get("buffer", [])
        # Create a new mesh and object
        objectName = self.filepath.split("\\")[-1].split(".")[0]
        mesh = bpy.data.meshes.new("TinyGladeMesh")
        obj = bpy.data.objects.new(objectName, mesh)
        bpy.context.collection.objects.link(obj)
        if prim_center.size > 0:
            prim_center_mesh = bpy.data.meshes.new("PrimCenterMesh")
            prim_center_obj = bpy.data.objects.new("PrimCenterObject", prim_center_mesh)
            bpy.context.collection.objects.link(prim_center_obj)
            prim_center_mesh.from_pydata(prim_center, [], [])
        if appear_pos.size > 0:
            appear_pos_mesh = bpy.data.meshes.new("AppearPosMesh")
            appear_pos_obj = bpy.data.objects.new("AppearPosObject", appear_pos_mesh)
            bpy.context.collection.objects.link(appear_pos_obj)
            appear_pos_mesh.from_pydata(appear_pos, [], [])
        # Assign geometry to mesh
        mesh.from_pydata(vertex_positions, [], faces)
        mesh.flip_normals()
        # if vertex_normals.size > 0:
         # mesh.normals_split_custom_set(vertex_normals)

        # --- handle vertex colors differently when importing trees ---
        if vertex_colors and self.import_type == 'TREE':
            # For tree files the color buffer encodes a UV in x/y and a canopy flag in z
            # build a UV map and an integer attribute instead of a color layer
            uv_data = []
            canopy_data = []
            for col in vertex_colors:
                # Expecting [x, y, z] float components
                uv_data.append((col[0], col[1]))
                # incoming z uses 1=trunk,0=canopy so flip to internal canopy flag
                canopy_data.append(1 - int(col[2]))

            # create or reuse a UV map to store the tree-specific UVs
            if not mesh.uv_layers:
                mesh.uv_layers.new(name="Vertex_UV")
            uv_layer = mesh.uv_layers.active.data
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    vertex_idx = mesh.loops[loop_idx].vertex_index
                    uv_layer[loop_idx].uv = uv_data[vertex_idx]

            # store canopy flag in a new point attribute
            canopy_attr = obj.data.attributes.new(name='is_canopy', type='INT', domain='POINT')
            for i, val in enumerate(canopy_data):
                canopy_attr.data[i].value = val

        elif vertex_colors:
            # standard color import path
            colattr = obj.data.color_attributes.new(
                name='Vertex_Color',
                type='FLOAT_COLOR',
                domain='POINT',
            )
            for v_index in range(len(obj.data.vertices)):
                color = vertex_colors[v_index]
                colattr.data[v_index].color = [color[0], color[1], color[2], 1.0]  # Assuming colors are in RGBA format

        if vertex_UV and self.import_type != 'TREE':
            if not mesh.uv_layers:
                mesh.uv_layers.new(name="Vertex_UV")  # Create a new UV map if none exists
            # Access the active UV layer
            uv_layer = mesh.uv_layers.active.data

            # Apply the UV coordinates to the UV map
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    vertex_idx = mesh.loops[loop_idx].vertex_index
                    uv_layer[loop_idx].uv = vertex_UV[vertex_idx]
        mesh.update()
        
        # Add custom attributes for material flags
        if is_metal:
            metal_attr = obj.data.attributes.new(name='is_metal_part', type='INT', domain='POINT')
            for i, val in enumerate(is_metal):
                metal_attr.data[i].value = int(val)
        
        if is_glass:
            glass_attr = obj.data.attributes.new(name='is_glass', type='INT', domain='POINT')
            for i, val in enumerate(is_glass):
                glass_attr.data[i].value = int(val)
        
        return {'FINISHED'}

    def draw(self, context):
        """Show import options in the file browser panel."""
        layout = self.layout
        layout.prop(self, "import_type")