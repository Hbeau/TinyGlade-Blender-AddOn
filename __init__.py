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
import bmesh
print(bpy.__file__)
import numpy as np
import json
from mathutils import Vector, Matrix
import math
from bpy_extras.io_utils import ExportHelper, ImportHelper

# Import Operator
class ImportTinyGladeJSON(bpy.types.Operator, ImportHelper):
    """Load a Tiny Glade JSON file"""
    bl_idname = "import_scene.tiny_glade_json"
    bl_label = "Import Tiny Glade JSON"
    bl_options = {'PRESET', 'UNDO'}

    filename_ext = ".json"

    def execute(self, context):
        # Open and parse the JSON file
        with open(self.filepath, 'r') as f:
            data = json.load(f)
        vertex_positions = np.array([self.__convert_blender_vector(Vector(v)) for v in data.get("Vertex_Position",{}).get("buffer", [])])
        vertex_normals = np.array([self.__convert_blender_vector(Vector(v)) for v in data.get("Vertex_Normal",{}).get("buffer", [])])
        vertex_colors = data.get("Vertex_Color",{}).get("buffer", [])
        vertex_UV = data.get("Vertex_UV",{}).get("buffer", [])
        indices = data.get("indices",{}).get("buffer", [])
        faces = [indices[i:i+3] for i in range(0, len(indices), 3)]
        prim_center = np.array([self.__convert_blender_vector(Vector(v)) for v in data.get("prim_center",{}).get("buffer", [])])
        appear_pos = np.array([self.__convert_blender_vector(Vector(v)) for v in data.get("appear_pos",{}).get("buffer", [])])
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
        if vertex_colors:
            colattr = obj.data.color_attributes.new(
                name='colname',
                type='FLOAT_COLOR',
                domain='POINT',
            )
            for v_index in range(len(obj.data.vertices)):
                color = vertex_colors[v_index] 
                print(f"Color for vertex {v_index}: {color}")
                colattr.data[v_index].color = [color[0], color[1], color[2], 1.0]  # Assuming colors are in RGBA format
        if vertex_UV:
            if not mesh.uv_layers:
                mesh.uv_layers.new(name="UVMap")  # Create a new UV map if none exists
            # Access the active UV layer
            uv_layer = mesh.uv_layers.active.data

            # Apply the UV coordinates to the UV map
            for poly in mesh.polygons:
                for loop_idx in poly.loop_indices:
                    vertex_idx = mesh.loops[loop_idx].vertex_index
                    uv_layer[loop_idx].uv = vertex_UV[vertex_idx]
        mesh.update()
        return {'FINISHED'}
    def __convert_blender_vector(self, vector:Vector): 
        return Vector((-vector.x, vector.z, vector.y))

# Export Operator
class ExportTinyGladeJSON(bpy.types.Operator, ExportHelper):
    """Save the mesh as Tiny Glade JSON"""
    bl_idname = "export_scene.tiny_glade_json"
    bl_label = "Export Tiny Glade JSON"
    
    bl_options = {'PRESET'}
    
    # Properties for file export
    filepath:  bpy.props.StringProperty(subtype="FILE_PATH",default="untitled.json")
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
    def execute(self, context):
        if not self.filepath.lower().endswith(self.filename_ext):
           self.filepath += self.filename_ext
        # Get the active mesh
        self.report({'INFO'}, f"Start Mesh Exportation")
        obj = context.object
        if obj is None or obj.type != 'MESH':
            self.report({'ERROR'}, "Selected object is not a mesh")
            return {'CANCELLED'}

        mesh = obj.data
        data = {'attributes': [], 'indices': None}

        # Populate data dictionary (Order matter!)
        if self.include_vertex_position:
            self.add_vertex_positions(obj, mesh, data)
            
        if self.include_vertex_normal:
            self.add_vertex_normals(mesh, data)
            
        if self.include_vertex_color:
            self.add_vertex_colors(mesh, data)

        if self.include_vertex_uv:
            self.add_vertex_UV(mesh, data)

        if self.include_faces_indices:
            self.add_faces_indices(mesh, data)

        # Save to file
        with open(self.filepath, 'w') as f:
            json.dump(data, f, separators=(',', ':'))

        self.report({'INFO'}, f"Exported data to {self.filepath}")
        return {'FINISHED'}

    def add_vertex_positions(self, obj, mesh, data):
        """Add vertex positions to the export data."""
        vertices = [Vector(obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
        vertices_oriented = [tuple(self.__convert_tiny_vector(v)) for v in vertices]
        data['Vertex_Position'] = {'type': ['float', 3], 'buffer': vertices_oriented}
        data['attributes'].append('Vertex_Position')
    
    def add_vertex_colors(self, mesh, data):
        """Add vertex colors to the export data."""
        if mesh.color_attributes:
            colors = [list(loop.color)[:-1] for loop in mesh.color_attributes.active.data]
            data['Vertex_Color'] = {'type': ['float', 3], 'buffer': colors}
            data['attributes'].append('Vertex_Color')

    def add_faces_indices(self, mesh, data):
        mesh = bpy.context.object.data
        mesh_copy = mesh.copy()

        # Créer un bmesh et le trianguler
        bm = bmesh.new()
        bm.from_mesh(mesh_copy)
        bmesh.ops.triangulate(bm, faces=bm.faces)

        # Appliquer les modifications au mesh copié
        bm.to_mesh(mesh_copy)
        bm.free()
        faces = []
        for poly in mesh.polygons:
            faces.extend(poly.vertices[:3])  # Only use the first three vertices (triangles)
        data['indices'] = {'type': ['int', 1], 'buffer': faces}
        bpy.data.meshes.remove(mesh_copy)

    def add_vertex_normals(self, mesh, data):
        """Add vertex normals to the export data."""
        vertex_normals = [tuple(self.__convert_tiny_vector(v.normal)) for v in mesh.vertices]
        data['Vertex_Normal'] = {'type': ['float', 3], 'buffer': vertex_normals}
        data['attributes'].append('Vertex_Normal')

    def add_vertex_UV(self, mesh, data):
        """Add vertex normals to the export data."""
        if mesh.uv_layers:
        # Access the active UV layer
            uv_layer =  [uv.uv[:] for uv in mesh.uv_layers.active.data]
        # Extract UV coordinates per loop and map to vertices
            uv_array = [None] * len(mesh.vertices)  # Initialize a list for UVs
            faces = []
            for poly in mesh.polygons:
                faces.extend(poly.vertices[:3])
            uv_map = {index: uv_layer[i] for i,index in enumerate(faces)}
            # Extract unique colors and map them back to their vertices
            seen_uv = {}
            for index, uv in uv_map.items():
                if index not in seen_uv.keys():
                    seen_uv[index] = uv


            # Sort by vertex index and get the unique colors
            uv_2d_array = [uv for _, uv in sorted(seen_uv.items())]
            # Convert to a 2D array format
            data['Vertex_UV'] = {'type': ['float', 2], 'buffer': uv_2d_array}
            data['attributes'].append('Vertex_UV')
    
    def __convert_tiny_vector(self, vector:Vector) : 
        return Vector((-vector.x, vector.z, vector.y))
    
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

# Add the Import/Export menus
def menu_func_import(self, context):
    self.layout.operator(ImportTinyGladeJSON.bl_idname, text="Tiny Glade JSON (.json)")

def menu_func_export(self, context):
    self.layout.operator(ExportTinyGladeJSON.bl_idname, text="Tiny Glade JSON (.json)")

# Register the add-on
def register():
    bpy.utils.register_class(ImportTinyGladeJSON)
    bpy.utils.register_class(ExportTinyGladeJSON)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ImportTinyGladeJSON)
    bpy.utils.unregister_class(ExportTinyGladeJSON)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
