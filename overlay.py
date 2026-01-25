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
import gpu
from gpu_extras.batch import batch_for_shader


def update_show_overlay_scene(self, context):
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces[0]
            if self.show_material_overlay:
                try:
                    if not hasattr(space, 'material_overlay_handler'):
                        space.material_overlay_handler = space.draw_handler_add(draw_material_overlay, (), 'WINDOW', 'POST_VIEW')
                except:
                    pass
            else:
                try:
                    if hasattr(space, 'material_overlay_handler'):
                        space.draw_handler_remove(space.material_overlay_handler, 'WINDOW')
                        del space.material_overlay_handler
                except AttributeError:
                    pass


def overlay_panel_draw(self, context):
    layout = self.layout
    layout.prop(context.scene, "show_material_overlay")


def draw_material_overlay():
    if not bpy.context.scene.show_material_overlay or bpy.context.mode != 'EDIT_MESH':
        return
    obj = bpy.context.edit_object
    if not obj or obj.type != 'MESH':
        return
    mesh = obj.data
    bm = bmesh.from_edit_mesh(mesh)
    metal_layer = bm.verts.layers.int.get('is_metal_part')
    glass_layer = bm.verts.layers.int.get('is_glass')
    if not metal_layer and not glass_layer:
        return
    shader = gpu.shader.from_builtin('FLAT_COLOR')
    matrix = obj.matrix_world
    positions = []
    colors = []
    for vert in bm.verts:
        metal = metal_layer and vert[metal_layer] == 1
        glass = glass_layer and vert[glass_layer] == 1
        if metal or glass:
            pos = matrix @ vert.co
            r = 1 if metal else 0
            b = 1 if glass else 0
            g = 0
            positions.append(pos)
            colors.append((r, g, b, 1))
    if positions:
        batch = batch_for_shader(shader, 'POINTS', {"pos": positions, "color": colors})
        gpu.state.point_size_set(10)
        batch.draw(shader)