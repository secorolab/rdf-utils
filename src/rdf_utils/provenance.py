# SPDX-License-Identifier:  MPL-2.0
"""Helpers for recording PROV-O provenance of generated RDF artifacts.

RDF/textX generators all describe a run the same way: the source models they
read (`prov:used`), the artifacts they wrote (`prov:wasGeneratedBy`) and the
tools that did it (`prov:wasAssociatedWith`). These functions add those nodes to
an `rdflib.Graph` using terms from `rdflib.namespace.PROV`, then serialize it as
JSON-LD against secorolab's shared ``prov.json`` context and validate it against
``prov.shacl.ttl``.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Union

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, XSD

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.naming import get_valid_filename
from rdf_utils.namespace import URL_MM_PROV_JSON, URL_MM_PROV_SHACL

Location = Union[URIRef, str, Path]
Time = Union[datetime, str]


def prov_context(prefix: str, namespace: URIRef | str, **extra: str) -> list:
    """Build a JSON-LD context for a provenance document.

    Parameters:
        prefix: short prefix for the generating tool's provenance namespace
        namespace: the tool's provenance namespace IRI
        extra: any additional prefix-to-IRI terms to inline

    Returns:
        A context usable as `rdflib.Graph.serialize(..., context=...)`: the shared
        secorolab ``prov.json`` followed by the tool's own prefix mapping.
    """
    return [URL_MM_PROV_JSON, {prefix: str(namespace), **extra}]


def utcnow_iso() -> str:
    """Current UTC time as an ISO-8601 string, for `started`/`ended`/`generated_at`."""
    return datetime.now(timezone.utc).isoformat()


def prov_iri(namespace: Any, *segments: Any) -> URIRef:
    """Mint a provenance node IRI from filename-safe path segments.

    Parameters:
        namespace: an `rdflib.Namespace` (or IRI base) for the generating tool
        segments: path segments, each slugged with `naming.get_valid_filename`,
                  e.g. ``prov_iri(ns, "entity", "source", "model.fsm")``

    Returns:
        ``namespace[seg1/seg2/...]`` as a URIRef.
    """
    return namespace["/".join(get_valid_filename(str(s)) for s in segments)]


def source_paths(model) -> list[Path]:
    """A textX model file and everything it transitively imported, de-duplicated.

    Parameters:
        model: a root textX model object

    Returns:
        Resolved paths in first-seen order, the source entities a generation used.
    """
    paths: dict[Path, None] = {}

    def visit(item) -> None:
        filename = getattr(item, "_tx_filename", None)
        if filename:
            paths[Path(filename).resolve()] = None
        for imp in getattr(item, "imports", []):
            for loaded in getattr(imp, "_tx_loaded_models", []):
                visit(loaded)

    visit(model)
    return list(paths)


def _location(value: Location) -> URIRef:
    if isinstance(value, URIRef):
        return value
    text = str(value)
    if "://" in text:
        return URIRef(text)
    return URIRef(Path(text).resolve().as_uri())


def _time(value: Time) -> Literal:
    text = value.isoformat() if isinstance(value, datetime) else value
    return Literal(text, datatype=XSD.dateTime)


def add_agent(graph: Graph, agent_id: URIRef, *types: URIRef) -> URIRef:
    """Add a `prov:Agent` node (a `prov:SoftwareAgent` unless told otherwise).

    `prov:Agent` is always asserted; `types` add specializations.

    Parameters:
        graph: the provenance graph to add to
        agent_id: IRI of the agent (the tool)
        types: extra agent types, e.g. `PROV.Person`; defaults to `PROV.SoftwareAgent`

    Returns:
        `agent_id`, so callers can reference it inline.
    """
    graph.add((agent_id, RDF.type, PROV.Agent))
    for type_id in types or (PROV.SoftwareAgent,):
        graph.add((agent_id, RDF.type, type_id))
    return agent_id


def add_activity(
    graph: Graph,
    activity_id: URIRef,
    *types: URIRef,
    used: Iterable[URIRef] = (),
    associated_with: URIRef | None = None,
    informed_by: URIRef | None = None,
    started: Time | None = None,
    ended: Time | None = None,
) -> URIRef:
    """Add a `prov:Activity` node describing one generation step.

    `prov:Activity` is always asserted; `types` add specializations.

    Parameters:
        graph: the provenance graph to add to
        activity_id: IRI of the activity
        types: extra activity types, e.g. a domain execution type
        used: source entities the activity read (`prov:used`)
        associated_with: the agent that ran it (`prov:wasAssociatedWith`)
        informed_by: an activity this one followed (`prov:wasInformedBy`)
        started, ended: timestamps, `datetime` or ISO-8601 string

    Returns:
        `activity_id`, so callers can reference it inline.
    """
    graph.add((activity_id, RDF.type, PROV.Activity))
    for type_id in types:
        graph.add((activity_id, RDF.type, type_id))
    for entity_id in used:
        graph.add((activity_id, PROV.used, entity_id))
    if associated_with is not None:
        graph.add((activity_id, PROV.wasAssociatedWith, associated_with))
    if informed_by is not None:
        graph.add((activity_id, PROV.wasInformedBy, informed_by))
    if started is not None:
        graph.add((activity_id, PROV.startedAtTime, _time(started)))
    if ended is not None:
        graph.add((activity_id, PROV.endedAtTime, _time(ended)))
    return activity_id


def add_entity(
    graph: Graph,
    entity_id: URIRef,
    *types: URIRef,
    at_location: Location | None = None,
    generated_by: URIRef | None = None,
    derived_from: URIRef | None = None,
    attributed_to: URIRef | None = None,
    generated_at: Time | None = None,
) -> URIRef:
    """Add a `prov:Entity` node for a source model or generated artifact.

    `prov:Entity` is always asserted; `types` add specializations.

    Parameters:
        graph: the provenance graph to add to
        entity_id: IRI of the entity
        types: extra entity types
        at_location: file/IRI location; local paths become `file://` IRIs
        generated_by: the activity that produced it (`prov:wasGeneratedBy`)
        derived_from: an entity it was derived from (`prov:wasDerivedFrom`)
        attributed_to: an agent it is attributed to (`prov:wasAttributedTo`)
        generated_at: generation timestamp, `datetime` or ISO-8601 string

    Returns:
        `entity_id`, so callers can reference it inline.
    """
    graph.add((entity_id, RDF.type, PROV.Entity))
    for type_id in types:
        graph.add((entity_id, RDF.type, type_id))
    if at_location is not None:
        graph.set((entity_id, PROV.atLocation, _location(at_location)))
    if generated_by is not None:
        graph.add((entity_id, PROV.wasGeneratedBy, generated_by))
    if derived_from is not None:
        graph.add((entity_id, PROV.wasDerivedFrom, derived_from))
    if attributed_to is not None:
        graph.add((entity_id, PROV.wasAttributedTo, attributed_to))
    if generated_at is not None:
        graph.add((entity_id, PROV.generatedAtTime, _time(generated_at)))
    return entity_id


def add_bundle(graph: Graph, bundle_id: URIRef) -> URIRef:
    """Add a `prov:Bundle` node naming the provenance document itself."""
    graph.add((bundle_id, RDF.type, PROV.Bundle))
    return bundle_id


# The kind of an input/output entity is a secorolab convention carried in the IRI
# path (``entity/<kind>/<file>``), not a PROV class -- so `add_source`/`add_generated`
# name it once here instead of every generator re-spelling the path. Same idea for the
# ``agent/<tool>`` and ``activity/<name>_generation/<stem>`` shapes below.
KIND_SOURCE = "source"
KIND_GENERATED = "generated"


def add_tool_agent(
    graph: Graph,
    namespace: Any,
    name: Any,
    *types: URIRef,
    version: str | None = None,
    repository: Location | None = None,
) -> URIRef:
    """Record the generating tool as an ``agent/<name>`` software agent.

    Version and repository use `dcterms:hasVersion` / `dcterms:references`, the terms
    the shared ``prov.json`` context defines (not a tool-specific version predicate).

    Parameters:
        graph: the provenance graph to add to
        namespace: the generating tool's provenance namespace
        name: short tool name (the IRI's last segment)
        types: extra agent types; defaults to `PROV.SoftwareAgent`
        version: the tool's version string
        repository: IRI/URL of the tool's source repository

    Returns:
        The agent IRI.
    """
    agent_id = prov_iri(namespace, "agent", name)
    add_agent(graph, agent_id, *types)
    if version is not None:
        graph.set((agent_id, DCTERMS.hasVersion, Literal(version)))
    if repository is not None:
        graph.set((agent_id, DCTERMS.references, _location(repository)))
    return agent_id


def add_generation_activity(
    graph: Graph,
    namespace: Any,
    target: str,
    stem: str,
    *types: URIRef,
    associated_with: URIRef | None = None,
    used: Iterable[URIRef] = (),
    at: Time | None = None,
) -> URIRef:
    """Record a generation step as an ``activity/<target>_generation/<stem>`` activity.

    Parameters:
        graph: the provenance graph to add to
        namespace: the generating tool's provenance namespace
        target: the generation target, e.g. ``cpp``/``jsonld``/``fsm``
        stem: the source model's file stem
        types: extra activity types
        associated_with: the agent that ran it (`prov:wasAssociatedWith`)
        used: source entities it read (`prov:used`)
        at: start/end timestamp; defaults to `utcnow_iso`

    Returns:
        The activity IRI.
    """
    at = at if at is not None else utcnow_iso()
    activity_id = prov_iri(namespace, "activity", f"{target}_generation", stem)
    return add_activity(
        graph, activity_id, *types, used=used, associated_with=associated_with,
        started=at, ended=at,
    )


def add_source(
    graph: Graph, namespace: Any, path: Location, *, used_by: URIRef | None = None
) -> URIRef:
    """Record a source model as an ``entity/source/<file>`` entity.

    Parameters:
        graph: the provenance graph to add to
        namespace: the generating tool's provenance namespace
        path: the source file (its name becomes the IRI's last segment)
        used_by: an activity that read it, linked via `prov:used`

    Returns:
        The source entity IRI.
    """
    entity_id = prov_iri(namespace, "entity", KIND_SOURCE, Path(str(path)).name)
    add_entity(graph, entity_id, at_location=path)
    if used_by is not None:
        graph.add((used_by, PROV.used, entity_id))
    return entity_id


def add_generated(
    graph: Graph,
    namespace: Any,
    path: Location,
    *,
    generated_by: URIRef,
    generated_at: Time | None = None,
    kind: str = KIND_GENERATED,
) -> URIRef:
    """Record an output artifact as an ``entity/<kind>/<file>`` entity.

    Parameters:
        graph: the provenance graph to add to
        namespace: the generating tool's provenance namespace
        path: the artifact file (its name becomes the IRI's last segment)
        generated_by: the activity that produced it (`prov:wasGeneratedBy`)
        generated_at: generation timestamp, `datetime` or ISO-8601 string
        kind: the entity-kind path segment; defaults to ``generated``

    Returns:
        The generated entity IRI.
    """
    entity_id = prov_iri(namespace, "entity", kind, Path(str(path)).name)
    add_entity(graph, entity_id, at_location=path, generated_by=generated_by,
               generated_at=generated_at)
    return entity_id


def validate_provenance(
    graph: Graph, shacl: dict[str, str] | None = None, quiet: bool = False
) -> bool:
    """Check a provenance graph against the PROV SHACL shapes.

    Parameters:
        graph: the provenance graph to check
        shacl: SHACL sources as ``path/URL -> format``; defaults to the shared
               ``prov.shacl.ttl``. Install a resolver for offline use.
        quiet: if true, return conformance instead of raising `SHACLViolation`
    """
    return check_shacl_constraints(graph, shacl or {URL_MM_PROV_SHACL: "turtle"}, quiet=quiet)


def write_provenance(
    graph: Graph,
    path: Path | str,
    *,
    context: list,
    validate: bool = True,
    shacl: dict[str, str] | None = None,
) -> Path:
    """Serialize a provenance graph to JSON-LD and (by default) validate it.

    Parameters:
        graph: the provenance graph to write
        path: destination file
        context: JSON-LD context, e.g. from `prov_context`
        validate: check against the PROV SHACL shapes before returning
        shacl: SHACL override forwarded to `validate_provenance`

    Returns:
        The written path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    graph.serialize(
        destination=path, format="json-ld", context=context, auto_compact=True, indent=2
    )
    if validate:
        validate_provenance(graph, shacl=shacl)
    return path


if __name__ == "__main__":
    # Self-check: record a one-step generation the way a consuming tool would.
    import tempfile
    from rdflib import Namespace

    ns = Namespace("https://example.org/tool/provenance/")
    graph = Graph()
    add_bundle(graph, ns["bundle/tool"])
    agent = add_tool_agent(graph, ns, "example_tool", version="1.2.3",
                           repository="https://github.com/secorolab/example")
    activity = add_generation_activity(graph, ns, "cpp", "model", associated_with=agent)
    add_source(graph, ns, "/tmp/model.fsm", used_by=activity)
    add_generated(graph, ns, "/tmp/model_fsm.hpp", generated_by=activity, generated_at=utcnow_iso())

    assert agent == ns["agent/example_tool"]
    assert (agent, RDF.type, PROV.Agent) in graph  # every agent is a prov:Agent
    assert (agent, DCTERMS.hasVersion, Literal("1.2.3")) in graph
    assert activity == ns["activity/cpp_generation/model"]
    assert (activity, PROV.used, ns["entity/source/model.fsm"]) in graph
    with tempfile.TemporaryDirectory() as directory:
        document = write_provenance(graph, Path(directory) / "provenance.ld.json",
                                    context=prov_context("ex", ns))  # serializes + validates
        assert Graph().parse(document, format="json-ld").value(
            activity, PROV.wasAssociatedWith
        ) == agent
    print("provenance self-check ok")
