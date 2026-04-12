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
from .mesh_presets import get_preset_manager


# Global storage for popover data (workaround for context.scene limitation during drawing)
_popover_data = {}


# Popover Panel for Full Mesh List
class EXPORT_PT_MeshListPopover(bpy.types.Panel):
    """Panel showing the full list of meshes in a popover"""
    bl_space_type = 'FILE_BROWSER'
    bl_region_type = 'WINDOW'
    bl_label = "Full Mesh List"
    bl_idname = "EXPORT_PT_mesh_list_popover"
    
    def draw(self, context):
        layout = self.layout
        meshes = _popover_data.get('remaining_meshes', [])
        if meshes:
            layout.label(text="Additional Meshes:")
            col = layout.column()
            col.scale_y = 0.75
            for mesh in meshes:
                col.label(text=f"  {mesh}")
        else:
            layout.label(text="No additional meshes")


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
        description="Export is_metal_part attribute, used in doors and trapdoors",
        default=False
    )
    include_is_glass: bpy.props.BoolProperty(
        name="Include Is Glass",
        description="Export is_glass attribute, usefull for windows",
        default=False
    )
    enable_preprocessing: bpy.props.BoolProperty(
        name="Enable Pre-processing",
        description="Enable pre-processing pipeline to apply 'edge split' and 'triangulation' before export." \
        "Disable it if you want to export raw mesh data without modifications.",
        default=True
    )
    
    def get_shader_items(self, context):
        manager = get_preset_manager()
        return [(preset, preset, "") for preset in manager.get_preset_list()]

    def get_mesh_items(self, context):
        manager = get_preset_manager()
        meshes = []
        for preset in manager.get_preset_list():
            meshes.extend(manager.get_meshes_for_preset(preset))
        mesh_list = sorted(set(meshes))
        return [(mesh, mesh, "") for mesh in mesh_list]

    def update_attributes_from_preset_selection(self, context):
        """Update attribute checkboxes based on selected preset's requirements"""
        manager = get_preset_manager()
        if not self.selected_preset:
            return
        
        common_attributes, optional_attributes = manager.get_attributes_for_preset(self.selected_preset)
        all_attrs = set(common_attributes) | set(optional_attributes)
        
        # Map attribute names to their corresponding property names
        attr_to_property = {
            'Vertex_Position': 'include_vertex_position',
            'Vertex_Color': 'include_vertex_color',
            'Vertex_Normal': 'include_vertex_normal',
            'Vertex_UV': 'include_vertex_uv',
            'is_metal_part': 'include_is_metal_part',
            'is_glass': 'include_is_glass',
        }
        
        # Update boolean properties based on required attributes
        for attr, prop_name in attr_to_property.items():
            if attr in common_attributes:
                # Required attributes are always checked and disabled (handled via UI)
                setattr(self, prop_name, True)

    def update_attributes_from_mesh_selection(self, context):
        """Update attribute checkboxes based on selected mesh's requirements"""
        manager = get_preset_manager()
        if not self.selected_mesh:
            return
        
        preset_info = manager.get_preset_for_mesh(self.selected_mesh)
        if not preset_info:
            return
        
        preset_name, common_attributes, optional_attributes = preset_info
        
        # Map attribute names to their corresponding property names
        attr_to_property = {
            'Vertex_Position': 'include_vertex_position',
            'Vertex_Color': 'include_vertex_color',
            'Vertex_Normal': 'include_vertex_normal',
            'Vertex_UV': 'include_vertex_uv',
            'is_metal_part': 'include_is_metal_part',
            'is_glass': 'include_is_glass',
        }
        
        # Update boolean properties based on required attributes
        for attr, prop_name in attr_to_property.items():
            if attr in common_attributes:
                # Required attributes are always checked
                setattr(self, prop_name, True)

    selected_preset: bpy.props.EnumProperty(
        name="Shader Type",
        description="Select shader presets",
        items=get_shader_items,
        update=update_attributes_from_preset_selection,
    )
    
    selected_mesh: bpy.props.EnumProperty(
        name="Mesh Name",
        description="Select meshes",
        items=get_mesh_items,
        update=update_attributes_from_mesh_selection,
        default=0,
    )

    selector_mode: bpy.props.EnumProperty(
        name="Selector Mode",
        description="Choose what to fill the selector with",
        items=[
            ('SHADER', "Shader", "Fill selector with shader names"),
            ('MESH', "Mesh", "Fill selector with mesh names"),
            ('MANUAL', "Manual", "Don't fill selector, let user choose")
        ],
        default='SHADER'
    )

    def draw(self, context):
        """Defines the layout in the file browser side panel."""
        layout = self.layout
        
        # Pre-processing section
        box = layout.box()
        box.label(text="Pre-processing:")
        box.prop(self, "enable_preprocessing")
        
        # Shader Preset section
        box = layout.box()
        box.label(text="Shader Preset", icon='PRESET')
        
        manager = get_preset_manager()
        
        # Check if Manual preset is selected
        is_manual_mode = (self.selector_mode == 'MANUAL')
        
        row = box.row(align=True)
        row.prop(self, "selector_mode", expand=True)

        if self.selector_mode == 'SHADER':
            box.prop(self, "selected_preset", text="Shader")
            selected_item = self.selected_preset
        elif self.selector_mode == 'MESH':
            box.prop(self, "selected_mesh", text="Mesh")
            selected_item = self.selected_mesh
        else:
            # Manual mode - show selector to switch modes
            row = box.row(align=True)
            box.label(text="Manual Mode - All attributes are editable", icon='INFO')
            selected_item = None

        if selected_item:
            # Details collapsible section                
            [details_header, detail_box] = box.panel("details",default_closed=True)
            details_header.label(text=f"Details: {selected_item}")
            
            if self.selector_mode == 'SHADER' and detail_box is not None:
                meshes = manager.get_meshes_for_preset(selected_item)
                common_attributes, optional_attributes = manager.get_attributes_for_preset(selected_item)

                detail_box.label(text="Required attributes:", icon='CHECKMARK')
                col = detail_box.column()
                col.scale_y = 0.75
                for attr in common_attributes:
                    col.label(text=f"  • {attr}")

                if optional_attributes:
                    detail_box.separator()
                    detail_box.label(text="Optional attributes:")
                    col = detail_box.column()
                    col.scale_y = 0.75
                    for attr in optional_attributes:
                        col.label(text=f"  ○ {attr}")

                detail_box.separator()
                detail_box.label(text="Sample meshes:", icon='MESH_DATA')
                col = detail_box.column()
                col.scale_y = 0.7
                for mesh_item in meshes[:10]:
                    col.label(text=f"    {mesh_item}")
                if len(meshes) > 10:
                    _popover_data['remaining_meshes'] = meshes[10:]
                    row = col.row()
                    row.popover(panel="EXPORT_PT_mesh_list_popover", text=f"    ... +{len(meshes) - 10} more")
            elif self.selector_mode == 'MESH' and detail_box is not None:
                preset_info = manager.get_preset_for_mesh(selected_item)
                if preset_info:
                    preset_name, common_attributes, optional_attributes = preset_info
                    detail_box.label(text=f"Preset: {preset_name}", icon='PRESET')

                    detail_box.label(text="Required attributes:", icon='CHECKMARK')
                    col = detail_box.column()
                    col.scale_y = 0.75
                    for attr in common_attributes:
                        col.label(text=f"  • {attr}")

                    if optional_attributes:
                        detail_box.separator()
                        detail_box.label(text="Optional attributes:")
                        col = detail_box.column()
                        col.scale_y = 0.75
                        for attr in optional_attributes:
                            col.label(text=f"  ○ {attr}")
                else:
                    detail_box.label(text="No preset mapping for this mesh", icon='ERROR')
        
        # Export Options section
        box = layout.box()
        box.label(text="Export Options:")
        
        # Get required and optional attributes based on current selection
        common_attributes, optional_attributes = [], []
        if not is_manual_mode:
            if self.selector_mode == 'SHADER' and self.selected_preset:
                common_attributes, optional_attributes = manager.get_attributes_for_preset(self.selected_preset)
            elif self.selector_mode == 'MESH' and self.selected_mesh:
                preset_info = manager.get_preset_for_mesh(self.selected_mesh)
                if preset_info:
                    preset_name, common_attributes, optional_attributes = preset_info
        
        # Helper function to draw attribute with proper state management
        def draw_attribute(subbox, prop_name, attr_name, is_required, is_optional, is_manual):
            row = subbox.row(align=True)
            is_absent = not (is_required or is_optional)
            
            # In manual mode, all checkboxes are fully editable
            if not is_manual:
                # Set property state based on attribute status
                if is_absent:
                    # Not in either required or optional - disable and uncheck
                    setattr(self, prop_name, False)
                elif is_required:
                    # Required - ensure it's checked
                    setattr(self, prop_name, True)
            
            row.prop(self, prop_name, text=attr_name)
            
            if not is_manual:
                if is_required:
                    row.label(text="(required)", icon='CHECKMARK')
                elif is_absent:
                    row.label(text="(not supported)", icon='CANCEL')
                
                # Disable if not allowed or required
                row.enabled = is_optional
        
        # Geometry subsection
        subbox = box.box()
        subbox.label(text="Attributes:")
        subbox.prop(self, "include_faces_indices")
        def is_attr_required(attr_name):
            return attr_name in common_attributes
        def is_attr_optional(attr_name):
            return attr_name in optional_attributes
        draw_attribute(subbox, "include_vertex_position", "Vertex Position", is_attr_required("Vertex_Position"), is_attr_optional("Vertex_Position"), is_manual_mode)
        draw_attribute(subbox, "include_vertex_normal", "Vertex Normal", is_attr_required("Vertex_Normal"), is_attr_optional("Vertex_Normal"), is_manual_mode)
        draw_attribute(subbox, "include_vertex_color", "Vertex Color", is_attr_required("Vertex_Color"), is_attr_optional("Vertex_Color"), is_manual_mode)
        draw_attribute(subbox, "include_vertex_uv", "UV map", is_attr_required("Vertex_UV"),is_attr_optional("Vertex_UV"), is_manual_mode)
        
        draw_attribute(subbox, "include_is_metal_part", "Is Metal", is_attr_required("is_metal_part"), is_attr_optional("is_metal_part"), is_manual_mode)
        draw_attribute(subbox, "include_is_glass", "Is Glass", is_attr_required("is_glass"), is_attr_optional("is_glass"), is_manual_mode)

    def execute(self, context):
        self.report({'INFO'}, f"Start Mesh Exportation")
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}
        if not self.filepath.lower().endswith(self.filename_ext):
           self.filepath += obj.name + self.filename_ext
        # Prepare an evaluated, triangulated mesh (non-destructive) if pre-processing is enabled
        if self.enable_preprocessing:
            mesh = pre_export_pipeline(context, obj)
        else:
            mesh = obj.data
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
        if mesh.color_attributes and mesh.color_attributes.values()[0] is not None:
            attr = mesh.color_attributes.values()[0]
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
    