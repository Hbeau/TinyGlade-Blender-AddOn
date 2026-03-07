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
import bmesh
from mathutils import Vector
from bpy_extras.io_utils import ExportHelper
from .utils import flip_vector_orientation, pre_export_pipeline, vertex_positions_data, vertex_normals_data, faces_indices_data, apply_edge_split


# Export Operator
class ExportTinyGladeJSON(bpy.types.Operator, ExportHelper):
    """Save the mesh as Tiny Glade JSON"""
    bl_idname = "export_scene.tiny_glade_json"
    bl_label = "Export Tiny Glade JSON"
    
    bl_options = {'PRESET'}
    
    # Properties for file export
    filepath:  bpy.props.StringProperty(subtype="FILE_PATH")
    filename_ext = ".json"  # Default file extension

    # Export options
    include_vertex_position: bpy.props.BoolProperty(
        name="Include Vertex Position",
        description="Export vertex positions",
        default=True
    )
    include_vertex_color: bpy.props.BoolProperty(
        name="Include Vertex Color",
        description="Export vertex colors",
        default=False
    )
    include_vertex_normal: bpy.props.BoolProperty(
        name="Include Vertex Normal",
        description="Export vertex normals",
        default=False
    )
    include_faces_indices: bpy.props.BoolProperty(
        name="Include Faces Indices",
        description="Export Faces (indices)",
        default=True
    )

    include_vertex_uv: bpy.props.BoolProperty(
        name="Include UV map",
        description="Export UV map",
        default=False
    )
    include_is_metal_part: bpy.props.BoolProperty(
        name="Include Is Metal",
        description="Export is_metal_part attribute",
        default=False
    )
    include_is_glass: bpy.props.BoolProperty(
        name="Include Is Glass",
        description="Export is_glass attribute",
        default=False
    )

    def execute(self, context):
        self.report({'INFO'}, f"Start Mesh Exportation")
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        if not self.filepath.lower().endswith(self.filename_ext):
           self.filepath += obj.name + self.filename_ext
        # Prepare an evaluated, triangulated mesh (non-destructive)
        mesh = pre_export_pipeline(context, obj)
        data = {'attributes': [], 'indices': None}

        # Populate data dictionary (Order matter!)
        try:
            if self.include_vertex_position:
                self.add_vertex_positions(obj, mesh, data)
            
            if self.include_vertex_normal:
                self.add_vertex_normals(mesh, data)
                
            if self.include_vertex_color:
                self.add_vertex_colors(mesh, data)

            if self.include_vertex_uv:
                self.add_vertex_UV(mesh, data)

            if self.include_is_metal_part:
                self.add_is_metal(mesh, data)

            if self.include_is_glass:
                self.add_is_glass(mesh, data)

            if self.include_faces_indices:
                self.add_faces_indices(mesh, data)
            # Save to file
            with open(self.filepath, 'w') as f:
                json.dump(data, f, separators=(',', ':'))

            self.report({'INFO'}, f"Exported data to {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}
        finally:
            # DEBUG: Keep temporary mesh for debugging purposes
            # Uncomment to clean up temporary mesh created by pre_export_pipeline
            #try:
            #    if temp_mesh and temp_mesh.name in bpy.data.meshes:
            #        bpy.data.meshes.remove(temp_mesh)
            #except Exception:
            #    pass
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

    def add_vertex_colors(self, mesh, data):
        """Add vertex colors to the export data."""
        if mesh.color_attributes and mesh.color_attributes.active:
            attr = mesh.color_attributes.active
            # Map corner/loop colors to first-seen per-vertex colors (Option A)
            print(f"Exporting vertex colors from attribute: {attr}")
            vertex_colors = [None] * len(mesh.vertices)
            if attr.domain == 'POINT':
                for i, elem in enumerate(attr.data):
                    col = list(elem.color)
                    vertex_colors[i] = [col[0], col[1], col[2]]
            else:
                # CORNER / LOOP domain
                for loop_idx, loop in enumerate(mesh.loops):
                    v_idx = loop.vertex_index
                    if vertex_colors[v_idx] is None:
                        col = list(attr.data[loop_idx].color)
                        vertex_colors[v_idx] = [col[0], col[1], col[2]]
            # Fallback for unset vertices
            for i in range(len(vertex_colors)):
                if vertex_colors[i] is None:
                    vertex_colors[i] = [1.0, 1.0, 1.0]
            data['Vertex_Color'] = {'type': ['float', 3], 'buffer': vertex_colors}
            data['attributes'].append('Vertex_Color')

    def add_vertex_UV(self, mesh, data):
        """Add vertex normals to the export data."""
        if mesh.uv_layers and mesh.uv_layers.active:
            uv_layer = mesh.uv_layers.active.data
            vertex_uv = [None] * len(mesh.vertices)
            for loop_idx, loop in enumerate(mesh.loops):
                v_idx = loop.vertex_index
                if vertex_uv[v_idx] is None:
                    uv = uv_layer[loop_idx].uv
                    vertex_uv[v_idx] = [uv[0], uv[1]]
            for i in range(len(vertex_uv)):
                if vertex_uv[i] is None:
                    vertex_uv[i] = [0.0, 0.0]
            data['Vertex_UV'] = {'type': ['float', 2], 'buffer': vertex_uv}
            data['attributes'].append('Vertex_UV')
    
    def add_is_metal(self, mesh, data):
        """Add is_metal attribute to the export data."""
        if 'is_metal_part' in mesh.attributes:
            attr = mesh.attributes['is_metal_part']
            # Map corner data to first-seen per-vertex if needed
            vertex_values = [None] * len(mesh.vertices)
            if attr.domain == 'POINT':
                for i, item in enumerate(attr.data):
                    vertex_values[i] = int(item.value)
            else:
                for loop_idx, loop in enumerate(mesh.loops):
                    v_idx = loop.vertex_index
                    if vertex_values[v_idx] is None:
                        vertex_values[v_idx] = int(attr.data[loop_idx].value)
            for i in range(len(vertex_values)):
                if vertex_values[i] is None:
                    vertex_values[i] = 0
            data['is_metal_part'] = {'type': ['int', 1], 'buffer': vertex_values}
            data['attributes'].append('is_metal_part')
    
    def add_is_glass(self, mesh, data):
        """Add is_glass attribute to the export data."""
        if 'is_glass' in mesh.attributes:
            attr = mesh.attributes['is_glass']
            vertex_values = [None] * len(mesh.vertices)
            if attr.domain == 'POINT':
                for i, item in enumerate(attr.data):
                    vertex_values[i] = int(item.value)
            else:
                for loop_idx, loop in enumerate(mesh.loops):
                    v_idx = loop.vertex_index
                    if vertex_values[v_idx] is None:
                        vertex_values[v_idx] = int(attr.data[loop_idx].value)
            for i in range(len(vertex_values)):
                if vertex_values[i] is None:
                    vertex_values[i] = 0
            data['is_glass'] = {'type': ['int', 1], 'buffer': vertex_values}
            data['attributes'].append('is_glass')
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    def draw(self, context):
        """Defines the layout in the file browser side panel."""
        layout = self.layout
        layout.label(text="Export Options:")
        layout.prop(self, "include_vertex_position")
        layout.prop(self, "include_faces_indices")
        layout.prop(self, "include_vertex_normal")
        layout.prop(self, "include_vertex_color")
        layout.prop(self, "include_vertex_uv")
        layout.prop(self, "include_is_metal_part")
        layout.prop(self, "include_is_glass")