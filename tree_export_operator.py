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
from bpy_extras.io_utils import ExportHelper
from .utils import flip_vector_orientation, pre_export_pipeline, vertex_positions_data, vertex_normals_data, faces_indices_data, apply_edge_split


# Export Operator (Tree-specific)
class ExportTinyGladeTreeJSON(bpy.types.Operator, ExportHelper):
    """Save a tree mesh as Tiny Glade JSON using tree-specific rules"""
    bl_idname = "export_scene.tiny_glade_tree_json"
    bl_label = "Export Tiny Glade Tree JSON"
    bl_options = {'PRESET'}

    # Only file path; no export options for trees (trees have fixed attributes)
    filepath:  bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext = ".json"

    appear_pos_source_mesh: bpy.props.StringProperty(
        name="Appear Pos Source Mesh",
        description="Select which mesh object to use as source for appear_pos",
        default=""
    )
    prim_center_source_mesh: bpy.props.StringProperty(
        name="Prim Center Source Mesh",
        description="Select which mesh object to use as source for prim_center",
        default=""
    )

    def execute(self, context):
        self.report({'INFO'}, "Start Tree Mesh Exportation")
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        if not self.filepath.lower().endswith(self.filename_ext):
           self.filepath += obj.name + self.filename_ext

        # Prepare mesh and metadata
        mesh = pre_export_pipeline(context, obj)
        data = {'attributes': []}

        try:
            # Always include these attributes for trees
            self.add_vertex_positions(obj, mesh, data)
            self.add_vertex_normals(mesh, data)
            # Tree-specific vertex colors (placeholder; tree logic differs)
            self.add_tree_vertex_colors(mesh, data)

            # appear_pos: tree-specific handler (may use meta if available)
            self.add_appear_pos(data)

            # prim_center: compute primitive/face centers for this mesh
            self.add_prim_center(data)

            # Also include indices for geometry consumers
            self.add_faces_indices(mesh, data)

            # Save to file
            with open(self.filepath, 'w') as f:
                json.dump(data, f, separators=(',', ':'))

            self.report({'INFO'}, f"Exported tree data to {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Tree export failed: {str(e)}")
            e.print_exc()
            return {'CANCELLED'}
        finally:
            self.report({'INFO'}, f"Debug mesh kept: {mesh.name}")

    def add_vertex_positions(self, obj, mesh, data):
        """Add vertex positions to the export data using shared helper."""

        data['Vertex_Position'] = {
            'type': ['float', 3],
            'buffer': vertex_positions_data(obj, mesh),
        }
        data['attributes'].append('Vertex_Position')
    

    def add_faces_indices(self, mesh, data):
        # `mesh` is expected to be already triangulated by pre_export_pipeline

        data['indices'] = {'type': ['int', 1], 'buffer': faces_indices_data(mesh)}

    def add_vertex_normals(self, mesh, data):
        """Add vertex normals to the export data using shared helper."""

        data['Vertex_Normal'] = {
            'type': ['float', 3],
            'buffer': vertex_normals_data(mesh),
        }
        data['attributes'].append('Vertex_Normal')

    def add_tree_vertex_colors(self, mesh, data):
        """Export the special tree encoding.

        For tree meshes we pack the per-vertex UV (stored on the mesh as the
        active UV layer) into the x/y components of the Vertex_Color buffer
        and use the z component as a canopy flag (0=trunk, 1=canopy).  A
        dedicated ``is_canopy`` integer attribute on the mesh is consulted
        if present; otherwise all vertices default to 0.
        """
        # gather UVs per vertex
        uv_coords = None
        if mesh.uv_layers and mesh.uv_layers.active:
            # map loops to the first seen vertex UV
            uv_coords = [None] * len(mesh.vertices)
            uv_layer = mesh.uv_layers.active.data
            for loop_idx, loop in enumerate(mesh.loops):
                v_idx = loop.vertex_index
                if uv_coords[v_idx] is None:
                    uv = uv_layer[loop_idx].uv
                    uv_coords[v_idx] = (uv[0], uv[1])
        # fallback if no UVs
        if uv_coords is None:
            uv_coords = [(0.0, 0.0)] * len(mesh.vertices)

        # gather canopy flag from attribute if available
        canopy_values = [0] * len(mesh.vertices)
        if 'is_canopy' in mesh.attributes:
            attr = mesh.attributes['is_canopy']
            if attr.domain == 'POINT':
                for i, item in enumerate(attr.data):
                    canopy_values[i] = int(item.value)
            else:
                for loop_idx, loop in enumerate(mesh.loops):
                    v_idx = loop.vertex_index
                    if canopy_values[v_idx] == 0:
                        canopy_values[v_idx] = int(attr.data[loop_idx].value)

        # build color buffer using uv + canopy
        vertex_colors = []
        for i in range(len(mesh.vertices)):
            if uv_coords[i] is None:
                uv_coords[i] = (0.0, 0.0)
            u, v = uv_coords[i]
            flag = canopy_values[i]
            # write out with inverted convention: 1=trunk,0=canopy
            vertex_colors.append([u, v, 1 - flag])

        data['Vertex_Color'] = {'type': ['float', 3], 'buffer': vertex_colors}
        data['attributes'].append('Vertex_Color')

    def add_appear_pos(self, data):
        """Add appear_pos to the export data using selected source mesh."""
        if not self.appear_pos_source_mesh:
            return
        try:
            source_obj = bpy.data.objects[self.appear_pos_source_mesh]
            if source_obj and source_obj.type == 'MESH':
                # Export vertex positions without transformation
                appear_pos = [(v.co.x, v.co.y, v.co.z) for v in source_obj.data.vertices]
                data['appear_pos'] = {'type': ['float', 3], 'buffer': appear_pos}
                data['attributes'].append('appear_pos')
        except KeyError:
            pass

    def add_prim_center(self, data):
        """Add prim_center to the export data using selected source mesh."""
        if not self.prim_center_source_mesh:
            return
        try:
            source_obj = bpy.data.objects[self.prim_center_source_mesh]
            if source_obj and source_obj.type == 'MESH':
                # Export vertex positions without transformation
                prim_center = [(v.co.x, v.co.y, v.co.z) for v in source_obj.data.vertices]
                data['prim_center'] = {'type': ['float', 3], 'buffer': prim_center}
                data['attributes'].append('prim_center')
        except KeyError:
            pass

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    def draw(self, context):
        """Defines the layout in the file browser side panel."""
        layout = self.layout
        layout.label(text="Export Options:")
        # Appear Pos Options
        layout.prop_search(self, "appear_pos_source_mesh", context.scene, "objects", text="Appear Pos Source Mesh")
        
        layout.prop_search(self, "prim_center_source_mesh", context.scene, "objects", text="Prim Center Source Mesh")