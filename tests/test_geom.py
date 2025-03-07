# SPDX-Litense-Identifier:  MPL-2.0
import unittest
import numpy as np
from rdflib import Dataset, Graph, Namespace
from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.geometry import (
    URI_QUDT_TYPE_DEG,
    PoseCoordModel,
    PositionCoordModel,
    get_coord_vectorxyz,
    get_euler_angles_abg,
    get_scipy_rotation,
)
from rdf_utils.resolver import install_resolver
from rdf_utils.uri import (
    URL_COMP_ROB2B,
    URL_MM_GEOM_COORD_JSON,
    URL_MM_GEOM_COORD_SECO_JSON,
    URL_MM_GEOM_JSON,
    URL_MM_GEOM_REL_JSON,
    URL_MM_GEOM_SHACL,
    URL_MM_QUDT_JSON,
    URL_SECORO_M,
)


KINOVA_GEOM_MODEL = f"{URL_COMP_ROB2B}/robot-models/kinova/gen3/7dof/robot.geom.json"
NS_ROB = Namespace(f"{URL_COMP_ROB2B}/robots/kinova/gen3/7dof/")

NS_TEST = Namespace(f"{URL_SECORO_M}/tests/collection/")
URI_TEST_POSE = NS_TEST["pose"]
URI_TEST_REF_ORIGIN = NS_TEST["frame-reference-origin"]
URI_TEST_BODY_ORIGIN = NS_TEST["frame-body-origin"]
URI_TEST_FRAME_REF = NS_TEST["frame-reference"]
URI_TEST_FRAME_BODY = NS_TEST["frame-body"]
URI_TEST_EULER_POSE = NS_TEST["pose-coord-euler"]
VALID_EULER_ANGLES = f"""
{{
    "@context": [
        "{URL_MM_QUDT_JSON}",
        "{URL_MM_GEOM_JSON}",
        "{URL_MM_GEOM_REL_JSON}",
        "{URL_MM_GEOM_COORD_JSON}",
        "{URL_MM_GEOM_COORD_SECO_JSON}"
    ],
    "@graph": [
        {{ "@id": "{URI_TEST_REF_ORIGIN}", "@type": "Point" }},
        {{ "@id": "{URI_TEST_BODY_ORIGIN}", "@type": "Point" }},
        {{
            "@id": "{URI_TEST_FRAME_REF}", "@type": "Frame",
            "origin": "{URI_TEST_REF_ORIGIN}"
        }},
        {{
            "@id": "{URI_TEST_FRAME_BODY}", "@type": "Frame",
            "origin": "{URI_TEST_BODY_ORIGIN}"
        }},
        {{
            "@id": "{URI_TEST_POSE}", "@type": "Pose",
            "of": "{URI_TEST_FRAME_BODY}", "with-respect-to": "{URI_TEST_FRAME_REF}"
        }},
        {{
            "@id": "{URI_TEST_EULER_POSE}",
            "@type": [
                "VectorXYZ", "PoseReference", "PoseCoordinate", "EulerAngles", "AnglesABG", "Intrinsic"
            ],
            "of-pose": "{URI_TEST_POSE}",
            "as-seen-by": "{URI_TEST_FRAME_REF}",
            "axes-sequence": "xyz",
            "unit": [ "M", "DEG" ],
            "alpha": 45.0, "beta": 0.0, "gamma": 0.0,
            "x": 10.0, "y": 5.0, "z": 0.0
        }}
    ]
}}
"""


class GeometryTest(unittest.TestCase):
    def setUp(self):
        install_resolver()

    def test_kinova_geom_model(self):
        kinova_ds = Dataset()
        kinova_ds.parse(KINOVA_GEOM_MODEL, format="json-ld")

        kinova_g = kinova_ds.graph(NS_ROB["geometry"])
        check_shacl_constraints(
            graph=kinova_g, shacl_dict={URL_MM_GEOM_SHACL: "turtle"}, quiet=False
        )

        pose_model = PoseCoordModel(
            coord_id=NS_ROB["pose-coord-link0-joint1-wrt-link0-root"], graph=kinova_g
        )
        _ = get_coord_vectorxyz(pose_model, kinova_g)

        position_model = PositionCoordModel(
            coord_id=NS_ROB["position-coord-link0-com-wrt-link0-root-origin"], graph=kinova_g
        )
        _ = get_coord_vectorxyz(position_model, kinova_g)

    def test_euler_geom_model(self):
        euler_g = Graph()
        euler_g.parse(data=VALID_EULER_ANGLES, format="json-ld")

        check_shacl_constraints(
            graph=euler_g, shacl_dict={URL_MM_GEOM_SHACL: "turtle"}, quiet=False
        )

        pose_model = PoseCoordModel(coord_id=URI_TEST_EULER_POSE, graph=euler_g)
        x, y, z = get_coord_vectorxyz(pose_model, euler_g)
        assert x == 10.0 and y == 5.0 and z == 0.0

        seq, is_intrinsic, unit, angles = get_euler_angles_abg(pose_model, euler_g)
        assert angles[0] == 45.0 and angles[1] == 0.0 and angles[2] == 0.0

        rot = get_scipy_rotation(pose_model, euler_g)
        if is_intrinsic:
            seq = seq.upper()
        scipy_angles = rot.as_euler(seq=seq, degrees=(unit == URI_QUDT_TYPE_DEG))
        assert np.allclose(angles, scipy_angles)
