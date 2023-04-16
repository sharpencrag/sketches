from maya import cmds
import re
from collections import defaultdict


facet_range_regex = re.compile('.*\[([0-9]*):([0-9]*)]')
single_facet_regex = re.compile('.*\[([0-9]*)]')


def bad_meshes_and_shaders():
    """return a nested dictionary with two keys, "face_shaded" and
    "multi_shaded" face_shaded nodes can be safely re-applied with the same
    shader on any of their faces, but multi_shaded nodes have multiple shaders
    on different faces, and cannot be trivially fixed"""
    result = dict()

    # these are nodes with at least two shaders attached to them,
    # even two of the same shader
    per_faces = per_face_shaded()

    # these are nodes with at least two different shaders attached
    multis = multi_shaded(per_faces)

    # reorganizes the multi-shaded nodes and culls the ones with only
    # duplicates of the same shader attached
    multi_shaded_result = shaders_by_obj(multis, cull=True)
    result['multi_shaded'] = multi_shaded_result

    # reorganize per_faces and only include nodes with a single shader
    face_shaded_result = {key: value for key, value
                          in shaders_by_obj(per_faces).items()
                          if key not in multi_shaded_result}
    result['face_shaded'] = face_shaded_result

    return result


def per_face_shaded():
    """get all nodes with any kind of per-face shading"""
    # get all the shading assignments in the scene.
    sg_nodes = {sg: (cmds.sets(sg, query=True) or [])
                for sg in cmds.ls(type='shadingEngine')}
    sg_and_meshes = []
    for sg, nodes in sg_nodes.items():
        # get the nodes with face-based shading
        bad = [(sg, node) for node in nodes if '.f[' in node]
        sg_and_meshes.extend(bad)
    return sg_and_meshes


def multi_shaded(per_face_shaded_nodes=None):
    """get all nodes with shaders attached to multiple groups of faces"""
    meshes = []
    per_face_shaded_nodes = per_face_shaded_nodes or per_face_shaded()
    for sg, node in per_face_shaded():
        shading_face_count = parse_facet_range(node)
        if face_count(node.split('.f[')[0]) != shading_face_count:
            meshes.append((sg, node))
    return meshes


def shaders_by_obj(nodes=None, cull=False):
    """Reorganize a collection of (shader, node) pairs into a dict with
    unique nodes as keys and unique shaders as values.  If cull is True,
    only multi-shaded nodes will be included"""
    nodes = nodes or multi_shaded()
    result_finder = defaultdict(set)
    for sg, obj in nodes:
        obj = obj.split('.f[')[0]
        result_finder[obj].add(sg)
    result = dict()
    for key, value in result_finder.items():
        value = tuple(value)
        if cull:
            if len(value) > 1:
                result[key] = value
        else:
            if len(value) == 1:
                result[key] = value[0]
            else:
                result[key] = value
    return result


def simple_cache(func):
    """cache an args-only function's result."""
    cache = dict()
    def decorated(*args):
        try:
            return cache[args]
        except KeyError:
            result = func(*args)
            cache[args] = result
            return result
    return decorated


@simple_cache
def face_count(obj):
    """return a tuple of the faces in a piece of geo.  This function gets
    called multiple times on any object with extreme multi-shading, so we
    cache the results for fast lookup."""
    count = cmds.polyEvaluate(obj, face=True)
    if isinstance(count, (int, long)):
        final_count = count - 1
    else:
        final_count = 0
    return (0, final_count)


def parse_facet_range(facet_indication):
    """take a face-range object notation from maya and return a tuple of
    integers.  For example:
    "myObject.f[1:12]" -> (1, 12)
    """
    facet_indication = str(facet_indication)
    range_match = re.match(facet_range_regex, facet_indication)
    if range_match:
        groups = range_match.groups()
        return (int(groups[0]), int(groups[1]))
    single_match = re.match(single_facet_regex, facet_indication)
    return int(single_match.groups()[0])


def fix_face_shading():
    """this function will find any meshes in which all faces are assigned the
    same shader, and apply the shader to the mesh instead of the faces."""

    # get all objects which have per-face shading but all the same shader"""
    face_shaded = bad_meshes_and_shaders()['face_shaded']

    for transform, shading_group in face_shaded.items():

        # bad_meshes_and_shaders returns transforms -- get the shape node
        mesh = cmds.listRelatives(transform, shapes=True)[0]

        # get and nuke the existing shader connections on the mesh
        conns = cmds.listConnections(mesh, connections=True,
                                     plugs=True, type='shadingEngine')
        for conn in conns:
            cmds.delete(conn, inputConnectionsAndNodes=True)

        # re-assign the shader
        cmds.sets([mesh], edit=True, forceElement=shading_group)

    return face_shaded.keys()

def select_multi_shaded():
    # get all objects which have per-face shading with different shaders
    multi_shaded = bad_meshes_and_shaders()['multi_shaded']
    cmds.select(multi_shaded.keys(), replace=True)
