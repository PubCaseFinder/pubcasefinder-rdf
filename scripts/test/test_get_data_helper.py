from rdflib import Graph, Literal
from rdflib.namespace import RDFS

from package import get_data_helper


def create_hpo_subclass_graph() -> Graph:
    graph = Graph()
    obo = get_data_helper.OBO
    graph.add((obo["HP_0000005"], RDFS.label, Literal("Mode of inheritance")))
    graph.add((obo["HP_0000006"], RDFS.subClassOf, obo["HP_0000005"]))
    graph.add((obo["HP_0000006"], RDFS.label, Literal("Autosomal dominant inheritance")))
    graph.add((obo["HP_0000007"], RDFS.subClassOf, obo["HP_0000005"]))
    graph.add((obo["HP_0000007"], RDFS.label, Literal("Autosomal recessive inheritance")))
    graph.add((obo["HP_0001417"], RDFS.subClassOf, obo["HP_0000007"]))
    graph.add((obo["HP_0001417"], RDFS.label, Literal("X-linked inheritance")))
    graph.add((obo["HP_9999999"], RDFS.subClassOf, obo["HP_0000118"]))
    graph.add((obo["HP_9999999"], RDFS.label, Literal("Unrelated phenotype")))
    return graph


def test_get_subclass_recursively_adds_descendants():
    graph = create_hpo_subclass_graph()
    inheritance_map_list = []

    get_data_helper.get_subclass(
        get_data_helper.OBO["HP_0000005"],
        inheritance_map_list,
        "HP:",
        "http://purl.obolibrary.org/obo/HP_",
        graph,
    )

    assert inheritance_map_list == [
        get_data_helper.inheritance_map(
            id="HP:0000006",
            en="Autosomal dominant inheritance",
            ja="",
        ),
        get_data_helper.inheritance_map(
            id="HP:0000007",
            en="Autosomal recessive inheritance",
            ja="",
        ),
        get_data_helper.inheritance_map(
            id="HP:0001417",
            en="X-linked inheritance",
            ja="",
        ),
    ]


def test_update_hpo_subclass_loads_root_and_descendants(tmp_path):
    hpo_owl_path = tmp_path / "hp.owl"
    create_hpo_subclass_graph().serialize(destination=str(hpo_owl_path), format="xml")

    inheritance_map_list = get_data_helper.update_hpo_subclass(
        hpo_owl_path,
        "0000005",
    )

    assert inheritance_map_list == [
        get_data_helper.inheritance_map(
            id="HP:0000005",
            en="Mode of inheritance",
            ja=None,
        ),
        get_data_helper.inheritance_map(
            id="HP:0000006",
            en="Autosomal dominant inheritance",
            ja="",
        ),
        get_data_helper.inheritance_map(
            id="HP:0000007",
            en="Autosomal recessive inheritance",
            ja="",
        ),
        get_data_helper.inheritance_map(
            id="HP:0001417",
            en="X-linked inheritance",
            ja="",
        ),
    ]
