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


def test_create_hpo_inheritance_en_ja_merges_previous_translations(tmp_path):
    inheritance_path = tmp_path / "HPO_Inheritance_en_jp.txt"
    old_content = (
        "HPO ID\t英語\t日本語\n"
        "HP:9999999\tAutosomal dominant inheritance\t常染色体優性遺伝\n"
        "HP:0000007\tAutosomal recessive inheritance\t常染色体劣性遺伝\n"
        "HP:0001450\tY-linked inheritance\tY連鎖遺伝\n"
    )
    inheritance_path.write_text(old_content, encoding="utf-8")

    get_data_helper.create_hpo_inheritance_en_ja(
        inheritance_path,
        [
            get_data_helper.inheritance_map(
                id="HP:0000006",
                en="Autosomal dominant inheritance",
                ja="",
            ),
            get_data_helper.inheritance_map(
                id="HP:0001417",
                en="X-linked inheritance",
                ja="",
            ),
            get_data_helper.inheritance_map(
                id="HP:0034345",
                en="Mendelian inheritance",
                ja=None,
            ),
        ],
    )

    assert inheritance_path.read_text(encoding="utf-8") == (
        "HPO ID\t英語\t日本語\n"
        "HP:0000006\tAutosomal dominant inheritance\t常染色体優性遺伝\n"
        "HP:0001417\tX-linked inheritance\t\n"
        "HP:0034345\tMendelian inheritance\t\n"
    )
    assert (tmp_path / "HPO_Inheritance_en_jp_old.txt").read_text(encoding="utf-8") == old_content
    assert (tmp_path / "HPO_Inheritance_en_jp_new.txt").read_text(encoding="utf-8") == (
        "HPO ID\t英語\t日本語\n"
        "HP:0000006\tAutosomal dominant inheritance\t\n"
        "HP:0001417\tX-linked inheritance\t\n"
        "HP:0034345\tMendelian inheritance\t\n"
    )


def test_check_hpo_inheritance_en_ja_returns_true_when_all_translated(tmp_path):
    inheritance_path = tmp_path / "HPO_Inheritance_en_jp.txt"
    inheritance_path.write_text(
        "HPO ID\t英語\t日本語\n"
        "HP:0000006\tAutosomal dominant inheritance\t常染色体優性遺伝\n"
        "HP:0000007\tAutosomal recessive inheritance\t常染色体劣性遺伝\n",
        encoding="utf-8",
    )

    assert get_data_helper.check_hpo_inheritance_en_ja(inheritance_path) is True


def test_check_hpo_inheritance_en_ja_returns_false_when_translation_is_missing(tmp_path):
    inheritance_path = tmp_path / "HPO_Inheritance_en_jp.txt"
    inheritance_path.write_text(
        "HPO ID\t英語\t日本語\n"
        "HP:0000006\tAutosomal dominant inheritance\t常染色体優性遺伝\n"
        "HP:0001417\tX-linked inheritance\t\n"
        "HP:0034345\tMendelian inheritance\n",
        encoding="utf-8",
    )

    assert get_data_helper.check_hpo_inheritance_en_ja(inheritance_path) is False


def test_iter_kegg_omim_mappings_extracts_omim_links(tmp_path):
    kegg_path = tmp_path / "disease"
    kegg_path.write_text(
        "ENTRY       H00001                      Disease\n"
        "NAME        Alpha disease\n"
        "DBLINKS     ICD-11: 123456789\n"
        "            OMIM: 100100 100200\n"
        "            MeSH: D000001\n"
        "///\n"
        "ENTRY       H00002                      Disease\n"
        "DBLINKS     OMIM: 100100\n"
        "            OMIM: 100100 100300\n"
        "///\n",
        encoding="utf-8",
    )

    assert list(get_data_helper.iter_kegg_omim_mappings(kegg_path)) == [
        ("100100", "H00001"),
        ("100200", "H00001"),
        ("100100", "H00002"),
        ("100300", "H00002"),
    ]


def test_create_kegg_disease_omim_tsv_writes_mapping_file(tmp_path):
    kegg_path = tmp_path / "disease"
    output_path = tmp_path / "KEGG_disease.tsv"
    kegg_path.write_text(
        "ENTRY       H02129                      Disease\n"
        "DBLINKS     OMIM: 100100\n"
        "///\n"
        "ENTRY       H01413                      Disease\n"
        "DBLINKS     OMIM: 100300 100400\n"
        "///\n",
        encoding="utf-8",
    )

    get_data_helper.create_kegg_disease_omim_tsv(kegg_path, output_path)

    assert output_path.read_text(encoding="utf-8") == (
        "100100\tH02129\n"
        "100300\tH01413\n"
        "100400\tH01413\n"
    )
