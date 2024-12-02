bl_info = {
    "name": "Tiny Glade JSON Import/Export",
    "blender": (2, 80, 0),
    "category": "Import-Export",
}

import bpy
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
        angle_radians = math.radians(90)  # Convert degrees to radians
        rotation_matrix = Matrix.Rotation(angle_radians, 4, 'X')
        vertex_positions = np.array([rotation_matrix @ Vector(v) for v in data.get("Vertex_Position",{}).get("buffer", [])])
        vertex_normals = np.array([rotation_matrix @ Vector(v) for v in data.get("Vertex_Normal",{}).get("buffer", [])])
        vertex_colors = data.get("Vertex_Color",{}).get("buffer", [])
        vertex_UV = data.get("Vertex_UV",{}).get("buffer", [])
        indices = data.get("indices",{}).get("buffer", [])
        faces = [indices[i:i+3] for i in range(0, len(indices), 3)]
        # Create a new mesh and object
        mesh = bpy.data.meshes.new("TinyGladeMesh")
        obj = bpy.data.objects.new("TinyGladeObject", mesh)
        bpy.context.collection.objects.link(obj)
        # Assign geometry to mesh
        mesh.from_pydata(vertex_positions, [], faces)
        mesh.normals_split_custom_set_from_vertices(vertex_normals)
        mesh.flip_normals()
        if not mesh.vertex_colors:
            mesh.vertex_colors.new()
        color_layer = mesh.vertex_colors.active
        # Assign colors to vertices
        for v in mesh.vertices: 
            color_layer.data[v.index].color = (*vertex_colors[v.index], 1.0)  # Add alpha value of 1.0
        mesh.update()
        return {'FINISHED'}

# Export Operator
class ExportTinyGladeJSON(bpy.types.Operator, ExportHelper):
    """Save the mesh as Tiny Glade JSON"""
    bl_idname = "export_scene.tiny_glade_json"
    bl_label = "Export Tiny Glade JSON"
    
    bl_options = {'PRESET'}
    
    # Properties for file export
    filepath: bpy.props.StringProperty(subtype="FILE_PATH",default="untitled.json")
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

        # Populate data dictionary
        if self.include_vertex_position:
            self.add_vertex_positions(obj, mesh, data)

        if self.include_vertex_color:
            self.add_vertex_colors(mesh, data)

        if self.include_faces_indices:
            self.add_faces_indices(mesh, data)

        if self.include_vertex_normal:
            self.add_vertex_normals(mesh, data)

        # Save to file
        with open(self.filepath, 'w') as f:
            json.dump(data, f, separators=(',', ':'))

        self.report({'INFO'}, f"Exported data to {self.filepath}")
        return {'FINISHED'}

    def add_vertex_positions(self, obj, mesh, data):
        """Add vertex positions to the export data."""
        angle_radians = math.radians(-90)  # Rotate -90 degrees around the X axis
        rotation_matrix = Matrix.Rotation(angle_radians, 4, 'X')
        vertices = [list(rotation_matrix @ obj.matrix_world @ vertex.co) for vertex in mesh.vertices]
        data['Vertex_Position'] = {'type': ['float', 3], 'buffer': vertices}
        data['attributes'].append('Vertex_Position')

    def add_vertex_colors(self, mesh, data):
        """Add vertex colors to the export data."""
        if mesh.vertex_colors:
            color_layer = [list(loop.color)[:-1] for loop in mesh.vertex_colors.active.data]
            data['Vertex_Color'] = {'type': ['float', 3], 'buffer': color_layer}
            data['attributes'].append('Vertex_Color')

    def add_faces_indices(self, mesh, data):
        """Add face indices to the export data."""
        # Ensure mesh is triangulated
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.quads_convert_to_tris()
        bpy.ops.object.mode_set(mode='OBJECT')

        faces = []
        for poly in mesh.polygons:
            faces.extend(poly.vertices[:3])  # Only use the first three vertices (triangles)
        data['indices'] = {'type': ['int', 1], 'buffer': faces}

    def add_vertex_normals(self, mesh, data):
        """Add vertex normals to the export data."""
        vertex_normals = [tuple(v.normal) for v in mesh.vertices]
        data['Vertex_Normal'] = {'type': ['float', 3], 'buffer': vertex_normals}
        data['attributes'].append('Vertex_Normal')
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

if __name__ == "__main__":
    register()
