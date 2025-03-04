# SPDX-Litense-Identifier:  MPL-2.0
from rdflib import Graph, URIRef
from rdf_utils.models.common import ModelBase
from rdf_utils.namespace import NS_MM_GEOM_COORD, NS_MM_GEOM_REL


URI_GEOM_TYPE_POSE = NS_MM_GEOM_REL["Pose"]
URI_GEOM_PRED_OF = NS_MM_GEOM_REL["of"]
URI_GEOM_PRED_WRT = NS_MM_GEOM_REL["with-respect-to"]
URI_GEOM_PRED_OF_POSE = NS_MM_GEOM_COORD["of-pose"]


class PoseCoordModel(ModelBase):
    pose: URIRef
    of: URIRef
    wrt: URIRef
    as_seen_by: URIRef

    def __init__(
        self,
        pose_coord_id: URIRef,
        graph: Graph,
    ) -> None:
        super().__init__(node_id=pose_coord_id, graph=graph)

        pose_id = graph.value(subject=self.id, predicate=URI_GEOM_PRED_OF_POSE)
        assert pose_id is not None and isinstance(
            pose_id, URIRef
        ), f"PoseCoordinate '{self.id}' does not have a valid 'of-pose' property: {pose_id}"
        self.pose = pose_id

        of_id = graph.value(subject=self.pose, predicate=URI_GEOM_PRED_OF)
        assert of_id is not None and isinstance(
            of_id, URIRef
        ), f"Pose '{self.pose}' does not have a valid 'of' property: {of_id}"
        self.of = of_id

        wrt_id = graph.value(subject=self.pose, predicate=URI_GEOM_PRED_WRT)
        assert wrt_id is not None and isinstance(
            wrt_id, URIRef
        ), f"Pose '{self.pose}' does not have a valid 'with-respect-to' property: {wrt_id}"
        self.wrt = wrt_id
