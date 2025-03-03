# SPDX-Litense-Identifier:  MPL-2.0
import unittest
from rdflib import Dataset, Graph
from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.resolver import install_resolver
from rdf_utils.uri import (
    URL_COMP_ROB2B,
    URL_MM_GEOM_COORD_JSON,
    URL_MM_GEOM_COORD_SCR_JSON,
    URL_MM_GEOM_JSON,
    URL_MM_GEOM_REL_JSON,
    URL_MM_GEOM_SHACL,
    URL_SECORO_M,
)


KINOVA_GEOM_MODEL = f"{URL_COMP_ROB2B}/robot-models/kinova/gen3/7dof/robot.geom.json"
URI_TEST = f"{URL_SECORO_M}/tests/collection"
URI_TEST_POSE = f"{URI_TEST}/pose"
URI_TEST_FRAME_REF = f"{URI_TEST}/frame-reference"
URI_TEST_FRAME_BODY = f"{URI_TEST}/frame-body"
URI_TEST_EULER_POSE = f"{URI_TEST}/pose-coord-euler"
VALID_EULER_ANGLES = f"""
{{
    "@context": [
        "{URL_MM_GEOM_JSON}",
        "{URL_MM_GEOM_REL_JSON}",
        "{URL_MM_GEOM_COORD_JSON}",
        "{URL_MM_GEOM_COORD_SCR_JSON}"
    ],
    "@graph": [
        {{
            "@id": "{URI_TEST_FRAME_REF}", "@type": "Frame"
        }},
        {{
            "@id": "{URI_TEST_FRAME_BODY}", "@type": "Frame"
        }},
        {{
            "@id": "{URI_TEST_POSE}", "@type": "Pose"
        }},
        {{
            "@id": "{URI_TEST_EULER_POSE}",
            "@type": [
                "PoseReference",
                "PoseCoordinate",
                "EulerAngles"
            ],
            "of-pose": "{URI_TEST_POSE}",
            "as-seen-by": "{URI_TEST_FRAME_REF}",
            "unit": [
                "M",
                "RAD"
            ],
            "alpha": 45.0,
            "beta": 0.0,
            "x": 10.0,
            "y": 5.0,
            "z": 0.0
        }}
    ]
}}
"""


class GeometryTest(unittest.TestCase):
    def setUp(self):
        install_resolver()

    def test_kinova_geom_model(self):
        kinova_g = Dataset()
        kinova_g.parse(KINOVA_GEOM_MODEL, format="json-ld")

        check_shacl_constraints(
            graph=kinova_g, shacl_dict={URL_MM_GEOM_SHACL: "turtle"}, quiet=False
        )

    def test_euler_geom_model(self):
        euler_g = Graph()
        euler_g.parse(data=VALID_EULER_ANGLES, format="json-ld")

        check_shacl_constraints(
            graph=euler_g, shacl_dict={URL_MM_GEOM_SHACL: "turtle"}, quiet=False
        )
