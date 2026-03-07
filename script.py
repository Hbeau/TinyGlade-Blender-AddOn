import bpy
import bmesh

# Assurez-vous qu'un objet est sélectionné
obj = bpy.context.active_object

if obj and obj.type == 'MESH':
    # Créer un nouveau mesh
    mesh = bpy.data.meshes.new("VertexMesh")
    new_obj = bpy.data.objects.new("VertexMeshObject", mesh)
    bpy.context.collection.objects.link(new_obj)

    bm = bmesh.new()   # create an empty BMesh
    bm.from_mesh(obj.data)   # fill it in from a Mesh

    # Créer une liste pour stocker les positions des vertices
    verts_positions = []

    # Parcourir toutes les faces et ajouter un vertex au centre de chaque face
    for vert in bm.verts:
        for face in vert.link_faces:
            center = face.calc_center_median()
            verts_positions.append(center)
            break
       

    # Créer des vertices dans le nouveau mesh
    new_verts = [bm.verts.new(pos) for pos in verts_positions]

    # Mettre à jour le mesh avec uniquement les nouveaux vertices
    mesh.from_pydata([v.co for v in new_verts], [], [])

    mesh.update()
    # Mettre à jour le mesh

    # Sélectionner le nouvel objet
    bpy.context.view_layer.objects.active = new_obj
    new_obj.select_set(True)
else:
    print("Veuillez sélectionner un objet de type MESH.")