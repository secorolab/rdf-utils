# SPDX-Litense-Identifier:  MPL-2.0
from rdflib import Graph, Literal, URIRef
from rdf_utils.models.common import ModelBase
from rdf_utils.namespace import NS_MM_GEOM, NS_MM_GEOM_COORD, NS_MM_GEOM_COORD_SCR, NS_MM_GEOM_REL


URI_GEOM_TYPE_POINT = NS_MM_GEOM["Point"]
URI_GEOM_TYPE_FRAME = NS_MM_GEOM["Frame"]
URI_GEOM_TYPE_POSE = NS_MM_GEOM_REL["Pose"]
URI_GEOM_TYPE_POSITION = NS_MM_GEOM_REL["Position"]
URI_GEOM_TYPE_ORIENT = NS_MM_GEOM_REL["Orientation"]
URI_GEOM_TYPE_POSITION_COORD = NS_MM_GEOM_COORD["PositionCoordinate"]
URI_GEOM_TYPE_POSITION_REF = NS_MM_GEOM_COORD["PositionReference"]
URI_GEOM_TYPE_ORIENT_COORD = NS_MM_GEOM_COORD["OrientationCoordinate"]
URI_GEOM_TYPE_ORIENT_REF = NS_MM_GEOM_COORD["OrientationReference"]
URI_GEOM_TYPE_POSE_COORD = NS_MM_GEOM_COORD["PoseCoordinate"]
URI_GEOM_TYPE_POSE_REF = NS_MM_GEOM_COORD["PoseReference"]
URI_GEOM_TYPE_VECTOR_XYZ = NS_MM_GEOM_COORD["VectorXYZ"]
URI_GEOM_TYPE_EULER_ANGLES = NS_MM_GEOM_COORD_SCR["EulerAngles"]
URI_GEOM_TYPE_QUATERNION = NS_MM_GEOM_COORD_SCR["Quaternion"]

URI_GEOM_PRED_ORIGIN = NS_MM_GEOM["origin"]
URI_GEOM_PRED_OF = NS_MM_GEOM_REL["of"]
URI_GEOM_PRED_WRT = NS_MM_GEOM_REL["with-respect-to"]
URI_GEOM_PRED_OF_POSE = NS_MM_GEOM_COORD["of-pose"]
URI_GEOM_PRED_OF_POSITION = NS_MM_GEOM_COORD["of-position"]
URI_GEOM_PRED_OF_ORIENT = NS_MM_GEOM_COORD["of-orientation"]
URI_GEOM_PRED_X = NS_MM_GEOM_COORD["x"]
URI_GEOM_PRED_Y = NS_MM_GEOM_COORD["y"]
URI_GEOM_PRED_Z = NS_MM_GEOM_COORD["z"]


class FrameModel(ModelBase):
    origin: URIRef

    def __init__(self, frame_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=frame_id, graph=graph)

        origin_id = graph.value(subject=self.id, predicate=URI_GEOM_PRED_ORIGIN)
        assert origin_id is not None and isinstance(
            origin_id, URIRef
        ), f"Frame '{self.id}' does not have a valid 'origin' property: {origin_id}"
        self.origin = origin_id


class PoseCoordModel(ModelBase):
    pose: URIRef
    of: FrameModel
    wrt: FrameModel
    as_seen_by: URIRef

    def __init__(self, coord_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=coord_id, graph=graph)

        assert URI_GEOM_TYPE_POSE_COORD in self.types, f"'{self.id}' is not a PoseCoordinate"

        assert URI_GEOM_TYPE_POSE_REF in self.types, f"'{self.id}' is not a PoseReference"
        pose_id = graph.value(subject=self.id, predicate=URI_GEOM_PRED_OF_POSE)
        assert pose_id is not None and isinstance(
            pose_id, URIRef
        ), f"PoseCoordinate '{self.id}' does not have a valid 'of-pose' property: {pose_id}"
        self.pose = pose_id

        of_id = graph.value(subject=self.pose, predicate=URI_GEOM_PRED_OF)
        assert of_id is not None and isinstance(
            of_id, URIRef
        ), f"Pose '{self.pose}' does not have a valid 'of' property: {of_id}"
        self.of = FrameModel(frame_id=of_id, graph=graph)

        wrt_id = graph.value(subject=self.pose, predicate=URI_GEOM_PRED_WRT)
        assert wrt_id is not None and isinstance(
            wrt_id, URIRef
        ), f"Pose '{self.pose}' does not have a valid 'with-respect-to' property: {wrt_id}"
        self.wrt = FrameModel(frame_id=wrt_id, graph=graph)


class PositionCoordModel(ModelBase):
    position: URIRef
    of: URIRef
    wrt: URIRef
    as_seen_by: URIRef

    def __init__(self, coord_id: URIRef, graph: Graph) -> None:
        super().__init__(node_id=coord_id, graph=graph)

        assert (
            URI_GEOM_TYPE_POSITION_COORD in self.types
        ), f"'{self.id}' is not a PositionCoordinate"

        assert URI_GEOM_TYPE_POSITION_REF in self.types, f"'{self.id}' is not a PositionReference"
        position_id = graph.value(subject=self.id, predicate=URI_GEOM_PRED_OF_POSITION)
        assert (
            position_id is not None and isinstance(position_id, URIRef)
        ), f"PositionCoordinate '{self.id}' does not have a valid 'of-position' property: {position_id}"
        self.position = position_id

        of_id = graph.value(subject=self.position, predicate=URI_GEOM_PRED_OF)
        assert of_id is not None and isinstance(
            of_id, URIRef
        ), f"Position '{self.position}' does not have a valid 'of' property: {of_id}"
        self.of = of_id

        wrt_id = graph.value(subject=self.position, predicate=URI_GEOM_PRED_WRT)
        assert wrt_id is not None and isinstance(
            wrt_id, URIRef
        ), f"Position '{self.position}' does not have a valid 'with-respect-to' property: {wrt_id}"
        self.wrt = wrt_id


def get_coord_vectorxyz(coord_model: ModelBase, graph: Graph) -> tuple[float, float, float]:
    assert (
        URI_GEOM_TYPE_VECTOR_XYZ in coord_model.types
    ), f"Coordinate '{coord_model.id}' is not of type 'VectorXYZ'"

    x_node = graph.value(subject=coord_model.id, predicate=URI_GEOM_PRED_X)
    assert isinstance(x_node, Literal) and isinstance(
        x_node.value, float
    ), f"Coordinate '{coord_model.id}' does not have a 'x' property of type float: {x_node}"

    y_node = graph.value(subject=coord_model.id, predicate=URI_GEOM_PRED_Y)
    assert isinstance(y_node, Literal) and isinstance(
        y_node.value, float
    ), f"Coordinate '{coord_model.id}' does not have a 'y' property of type float: {y_node}"

    z_node = graph.value(subject=coord_model.id, predicate=URI_GEOM_PRED_Z)
    assert isinstance(z_node, Literal) and isinstance(
        z_node.value, float
    ), f"Coordinate '{coord_model.id}' does not have a 'z' property of type float: {z_node}"

    return (x_node.value, y_node.value, z_node.value)
