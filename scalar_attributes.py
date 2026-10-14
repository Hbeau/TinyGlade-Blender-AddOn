import json

import bpy


_METADATA_KEY = "tiny_glade_scalar_attribute_metadata"


class ScalarGroupSelectionItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()
    group_name: bpy.props.StringProperty()
    selected: bpy.props.BoolProperty(default=False)


def scalar_buffers(data):
    """Yield named scalar attribute buffers declared in Tiny Glade JSON."""
    names = list(data.get("attributes", []))
    names.extend(
        name for name, attribute in data.items()
        if name not in names
        and name != "indices"
        and isinstance(attribute, dict)
        and "type" in attribute
        and "buffer" in attribute
    )
    for name in names:
        if name == "indices":
            continue
        attribute = data.get(name)
        if not isinstance(attribute, dict):
            continue
        attribute_type = attribute.get("type", [])
        if len(attribute_type) != 2 or attribute_type[1] != 1:
            continue
        yield name, attribute_type[0], attribute.get("buffer", [])


def add_scalar_vertex_groups(obj, data):
    """Import every declared scalar buffer as a named vertex group."""
    metadata = {}
    vertex_count = len(obj.data.vertices)

    for name, value_type, values in scalar_buffers(data):
        if len(values) != vertex_count:
            raise ValueError(
                f"Scalar attribute '{name}' has {len(values)} values for "
                f"{vertex_count} vertices"
            )

        numeric_values = [float(value) for value in values]
        minimum = min(numeric_values, default=0.0)
        maximum = max(numeric_values, default=0.0)
        needs_range = minimum < 0.0 or maximum > 1.0
        group_values = numeric_values

        if needs_range:
            if maximum == minimum:
                group_values = [0.5] * vertex_count
            else:
                value_range = maximum - minimum
                group_values = [
                    (value - minimum) / value_range for value in numeric_values
                ]
            metadata[name] = {
                "type": value_type,
                "minimum": minimum,
                "maximum": maximum,
            }
        elif value_type != "float":
            metadata[name] = {"type": value_type}

        group = obj.vertex_groups.new(name=name)
        for index, weight in enumerate(group_values):
            group.add([index], min(1.0, max(0.0, weight)), 'REPLACE')

    obj[_METADATA_KEY] = json.dumps(metadata)


def scalar_group_metadata(obj):
    try:
        return json.loads(obj.get(_METADATA_KEY, "{}"))
    except (TypeError, ValueError):
        return {}


def add_vertex_group_buffer(obj, mesh, group, data, attribute_name=None):
    """Export one vertex group as a scalar JSON attribute."""
    attribute_name = attribute_name or group.name
    if attribute_name in data or attribute_name == "indices":
        return

    values = [0.0] * len(mesh.vertices)
    for index, vertex in enumerate(mesh.vertices):
        for assignment in vertex.groups:
            if assignment.group == group.index:
                values[index] = float(assignment.weight)
                break

    all_metadata = scalar_group_metadata(obj)
    metadata = all_metadata.get(group.name, all_metadata.get(attribute_name, {}))
    if "minimum" in metadata and "maximum" in metadata:
        minimum = float(metadata["minimum"])
        maximum = float(metadata["maximum"])
        values = [minimum + value * (maximum - minimum) for value in values]

    value_type = metadata.get("type", "float")
    if value_type == "int":
        values = [int(round(value)) for value in values]

    data[attribute_name] = {
        "type": [value_type, 1],
        "buffer": values,
    }
    data.setdefault("attributes", []).append(attribute_name)


def sync_scalar_group_selection(
    operator,
    obj,
    attribute_names=None,
    required_names=(),
    default_selected=False,
    preserve_attribute_names=False,
):
    previous = {
        item.name: (item.selected, item.group_name)
        for item in operator.scalar_groups
    }
    previous_by_group = {
        item.group_name: (item.selected, item.name)
        for item in operator.scalar_groups if item.group_name
    }
    group_names = {group.name for group in obj.vertex_groups} if obj else set()
    if attribute_names is None:
        attribute_names = list(group_names)
    operator.scalar_groups.clear()
    required_names = set(required_names)
    for name in attribute_names:
        item = operator.scalar_groups.add()
        previous_state = previous.get(name) or previous_by_group.get(name)
        item.name = (
            previous_state[1]
            if preserve_attribute_names and previous_state and name in group_names
            else name
        )
        item.group_name = (
            name
            if name in group_names
            else previous_state[1]
            if previous_state and previous_state[1] in group_names
            else name if name in group_names else ""
        )
        item.selected = (
            True if name in required_names
            else previous_state[0]
            if previous_state
            else default_selected and name in group_names
        )


def draw_scalar_group_selection(
    layout,
    operator,
    obj,
    allowed_names=None,
    required_names=(),
    editable_attribute_names=False,
):
    box = layout.box()
    box.label(text="Scalar Attributes:")
    visible_count = 0
    required_names = set(required_names)
    for item in operator.scalar_groups:
        if allowed_names is not None and item.name not in allowed_names:
            continue
        visible_count += 1
        row = box.row(align=True)
        if item.name in required_names:
            row.label(text=item.name, icon='CHECKMARK')
        else:
            row.prop(item, "selected", text="")
            if editable_attribute_names:
                row.prop(item, "name", text="")
            else:
                row.label(text=item.name)
        row.prop_search(item, "group_name", obj, "vertex_groups", text="Group")
    if visible_count == 0:
        box.label(text="No matching vertex groups", icon='INFO')