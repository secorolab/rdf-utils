# SPDX-Litense-Identifier:  MPL-2.0
from typing import Optional
from rdflib import Graph, URIRef
from rdf_utils.models.common import ModelBase


class PoseCoordModel(ModelBase):
    def __init__(
        self,
        pose_coord_id: URIRef,
        graph: Optional[Graph] = None,
        types: Optional[set[URIRef]] = None,
    ) -> None:
        super().__init__(pose_coord_id, graph, types)

        pass
