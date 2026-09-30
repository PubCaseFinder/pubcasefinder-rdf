from io import StringIO
import xml.etree.ElementTree as ET

import duckdb
import pytest
from rdflib import Graph
from rdflib.compare import isomorphic

from package import disease_phenotype_association_util

hpoa_content = """
#description: "HPO annotations for rare diseases [8576: OMIM; 47: DECIPHER; 4337 ORPHANET]"
#version: 2026-01-08
#tracker: https://github.com/obophenotype/human-phenotype-ontology/issues
#hpo-version: http://purl.obolibrary.org/obo/hp/releases/2026-01-08/hp.json
database_id	disease_name	qualifier	hpo_id	reference	evidence	onset	frequency	sex	modifier	aspect	biocuration
OMIM:619340	Developmental and epileptic encephalopathy 96		HP:0011097	PMID:31675180	PCS		1/2			P	HPO:probinson[2021-06-21]
OMIM:619340	Developmental and epileptic encephalopathy 96		HP:0002187	PMID:31675180	PCS		1/1			P	HPO:probinson[2021-06-21]
OMIM:619340	Developmental and epileptic encephalopathy 96		HP:0001518	PMID:31675180	PCS		1/2			P	HPO:probinson[2021-06-21]
OMIM:619340	Developmental and epileptic encephalopathy 96		HP:0032792	PMID:31675180	PCS		1/2			P	HPO:probinson[2021-06-21]
OMIM:619340	Developmental and epileptic encephalopathy 96		HP:0011451	PMID:31675180	PCS		1/2			P	HPO:probinson[2021-06-21]
"""

product4_content = """\
<?xml version="1.0" encoding="UTF-8"?>
<JDBOR>
  <HPODisorderSetStatusList>
    <HPODisorderSetStatus>
      <Disorder>
        <OrphaCode> 58 </OrphaCode>
        <HPODisorderAssociationList>
          <HPODisorderAssociation>
            <HPO>
              <HPOId>HP:0000256</HPOId>
            </HPO>
            <HPOFrequency>
              <Name lang="en">Very frequent (99-80%)</Name>
            </HPOFrequency>
          </HPODisorderAssociation>
          <HPODisorderAssociation>
            <HPO>
              <HPOId>HP:0000256</HPOId>
            </HPO>
            <HPOFrequency>
              <Name lang="en">Frequent (79-30%)</Name>
            </HPOFrequency>
          </HPODisorderAssociation>
          <HPODisorderAssociation>
            <HPO>
              <HPOId> HP:0001249 </HPOId>
            </HPO>
            <HPOFrequency>
              <Name lang="en">Frequent (79-30%)</Name>
            </HPOFrequency>
          </HPODisorderAssociation>
          <HPODisorderAssociation>
            <HPO>
              <HPOId>HP:0001250</HPOId>
            </HPO>
          </HPODisorderAssociation>
          <HPODisorderAssociation>
            <HPO>
              <HPOId>HP:0001257</HPOId>
            </HPO>
            <HPOFrequency/>
          </HPODisorderAssociation>
          <HPODisorderAssociation>
            <HPOFrequency>
              <Name lang="en">Occasional (29-5%)</Name>
            </HPOFrequency>
          </HPODisorderAssociation>
        </HPODisorderAssociationList>
      </Disorder>
      <Disorder>
        <OrphaCode>166024</OrphaCode>
        <HPODisorderAssociationList>
          <HPODisorderAssociation>
            <HPO>
              <HPOId>HP:0011097</HPOId>
            </HPO>
            <HPOFrequency>
              <Name lang="en">Occasional (29-5%)</Name>
            </HPOFrequency>
          </HPODisorderAssociation>
        </HPODisorderAssociationList>
      </Disorder>
    </HPODisorderSetStatus>
  </HPODisorderSetStatusList>
</JDBOR>
"""


def test_load_ordo_frequency_annotations(tmp_path):
    product4_path = tmp_path / "en_product4.xml"
    product4_path.write_text(product4_content, encoding="utf-8")

    frequency_map = disease_phenotype_association_util.load_ordo_frequency_annotations(product4_path)

    expect_frequency_map = {
        "58\t0000256": "Very frequent (99-80%)",
        "58\t0001249": "Frequent (79-30%)",
        "166024\t0011097": "Occasional (29-5%)",
    }
    assert frequency_map == expect_frequency_map


def test_load_manual_phenotype_associations(tmp_path):
    hpoa_path = tmp_path / 'phenotype.hpoa'
    hpoa_path.write_text(hpoa_content, encoding="utf-8")
    manual_association_map = disease_phenotype_association_util.load_manual_phenotype_associations(hpoa_path, 'OMIM')
    expect_manual_association_map = {
        '619340\t0011097': 'Manual',
        '619340\t0002187': 'Manual',
        '619340\t0001518': 'Manual',
        '619340\t0032792': 'Manual',
        '619340\t0011451': 'Manual',
    }

    assert manual_association_map == expect_manual_association_map


def test_extract_frequency_label():
    hpo_frequency_element = ET.fromstring(
        '<HPOFrequency><Name lang="en"> Frequent (79-30%) </Name></HPOFrequency>'
    )

    assert disease_phenotype_association_util.extract_frequency_label(
        hpo_frequency_element
    ) == "Frequent (79-30%)"
    assert disease_phenotype_association_util.extract_frequency_label(None) is None
    assert disease_phenotype_association_util.extract_frequency_label(
        ET.fromstring("<HPOFrequency/>")
    ) is None


def test_normalize_hpo_id():
    assert disease_phenotype_association_util.normalize_hpo_id(" HP:0000256 ") == "0000256"
    assert disease_phenotype_association_util.normalize_hpo_id("0000256") == "0000256"


def test_create_annotation_source():
    source = disease_phenotype_association_util.create_annotation_source(
        disease_phenotype_association_util.HPOA_SOURCE,
        "Orphanet",
        "https://example.org/en_product4.xml",
    )

    assert source == disease_phenotype_association_util.AnnotationSource(
        source=disease_phenotype_association_util.HPOA_SOURCE,
        creator="Orphanet",
        page="https://example.org/en_product4.xml",
    )


def test_write_ordo_phenotype_association_ttl(tmp_path):
    output_path = tmp_path / "Orphanet_HP_Association.ttl"
    source = disease_phenotype_association_util.create_annotation_source(
        disease_phenotype_association_util.HPOA_SOURCE,
        "Orphanet",
        disease_phenotype_association_util.HPOA_PAGE,
    )
    manual_associations = {
        "58\t0000256": "Manual",
        "166024\t0011097": "Manual",
    }
    frequency_by_association = {
        "58\t0000256": "Very frequent (99-80%)",
    }

    disease_phenotype_association_util.write_ordo_phenotype_association_ttl(
        output_path,
        manual_associations,
        frequency_by_association,
        source,
    )

    actual_graph = Graph().parse(str(output_path), format="turtle")
    expect_graph = Graph().parse(
        data=f"""
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX hoom: <http://www.semanticweb.org/ontology/HOOM#>
PREFIX hpoa: <http://compbio.charite.de/jenkins/job/hpo.annotations.current/lastSuccessfulBuild/artifact/current/>
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX ordo: <http://www.orpha.net/ORDO/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:ORDO:58/phenotype:HP:0000256>
    a oa:Annotation ;
    oa:hasTarget ordo:Orphanet_58 ;
    oa:hasBody obo:HP_0000256 ;
    hoom:with_frequency obo:HP_0040281 ;
    dcterms:source hpoa:phenotype.hpoa ;
    obo:ECO_9000001 obo:ECO_0000218 .

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:ORDO:166024/phenotype:HP:0011097>
    a oa:Annotation ;
    oa:hasTarget ordo:Orphanet_166024 ;
    oa:hasBody obo:HP_0011097 ;
    dcterms:source hpoa:phenotype.hpoa ;
    obo:ECO_9000001 obo:ECO_0000218 .

hpoa:phenotype.hpoa
    dcterms:creator "{source.creator}" ;
    foaf:page <{source.page}> .

obo:HP_0040280 rdfs:label "Obligate (100%)"@en .
obo:HP_0040281 rdfs:label "Very frequent (99-80%)"@en .
obo:HP_0040282 rdfs:label "Frequent (79-30%)"@en .
obo:HP_0040283 rdfs:label "Occasional (29-5%)"@en .
obo:HP_0040284 rdfs:label "Very rare (<4-1%)"@en .
obo:HP_0040285 rdfs:label "Excluded (0%)"@en .
""",
        format="turtle"
    )

    assert len(actual_graph) == 19
    assert isomorphic(actual_graph, expect_graph)


def test_write_manual_phenotype_association_ttl(tmp_path):
    output_path = tmp_path / "OMIM_HP_Association.ttl"
    source = disease_phenotype_association_util.create_annotation_source(
        disease_phenotype_association_util.HPOA_SOURCE,
        "Human Phenotype Ontology Consortium",
        disease_phenotype_association_util.HPOA_PAGE,
    )
    manual_associations = {
        "619340\t0011097": "Manual",
        "619340\t0002187": "Manual",
    }

    disease_phenotype_association_util.write_manual_phenotype_association_ttl(
        output_path,
        "OMIM",
        "mim",
        "https://omim.org/entry/",
        manual_associations,
        source,
    )

    actual_graph = Graph().parse(str(output_path), format="turtle")
    expect_graph = Graph().parse(
        data=f"""
PREFIX dcterms: <http://purl.org/dc/terms/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX hpoa: <http://compbio.charite.de/jenkins/job/hpo.annotations.current/lastSuccessfulBuild/artifact/current/>
PREFIX mim: <https://omim.org/entry/>
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:OMIM:619340/phenotype:HP:0011097>
    a oa:Annotation ;
    oa:hasTarget mim:619340 ;
    oa:hasBody obo:HP_0011097 ;
    dcterms:source hpoa:phenotype.hpoa ;
    obo:ECO_9000001 obo:ECO_0000218 .

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:OMIM:619340/phenotype:HP:0002187>
    a oa:Annotation ;
    oa:hasTarget mim:619340 ;
    oa:hasBody obo:HP_0002187 ;
    dcterms:source hpoa:phenotype.hpoa ;
    obo:ECO_9000001 obo:ECO_0000218 .

hpoa:phenotype.hpoa
    dcterms:creator "{source.creator}" ;
    foaf:page <{source.page}> .
""",
        format="turtle"
    )

    assert len(actual_graph) == 12
    assert isomorphic(actual_graph, expect_graph)


def test_build_ordo_annotations():
    annotations = disease_phenotype_association_util.build_ordo_annotations(
        {
            "58\t0000256": "Manual",
            "166024\t0011097": "Manual",
        },
        {
            "58\t0000256": "Very frequent (99-80%)",
        },
    )

    assert annotations == [
        disease_phenotype_association_util.OrdoPhenotypeAnnotation(
            ordo_id="58",
            hpo_id="0000256",
            frequency_term_id="0040281",
        ),
        disease_phenotype_association_util.OrdoPhenotypeAnnotation(
            ordo_id="166024",
            hpo_id="0011097",
            frequency_term_id=None,
        ),
    ]


def test_write_frequency_labels():
    writer = StringIO()

    disease_phenotype_association_util.write_frequency_labels(writer)

    assert writer.getvalue() == (
        "obo:HP_0040280\n"
        '    rdfs:label "Obligate (100%)"@en .\n'
        "obo:HP_0040281\n"
        '    rdfs:label "Very frequent (99-80%)"@en .\n'
        "obo:HP_0040282\n"
        '    rdfs:label "Frequent (79-30%)"@en .\n'
        "obo:HP_0040283\n"
        '    rdfs:label "Occasional (29-5%)"@en .\n'
        "obo:HP_0040284\n"
        '    rdfs:label "Very rare (<4-1%)"@en .\n'
        "obo:HP_0040285\n"
        '    rdfs:label "Excluded (0%)"@en .\n'
    )


@pytest.mark.parametrize("frequency", ["0/2", "0/12", "0%", "0.0%", "HP:0040285", " 0/2 "])
def test_zero_frequency(frequency):
    assert disease_phenotype_association_util.is_zero_frequency(frequency)


@pytest.mark.parametrize("frequency", ["", " ", "1/2", "2/2", "0.01%", "100%"] +
                         [f"HP:004028{i}" for i in range(5)])
def test_positive_or_unspecified_frequency(frequency):
    assert not disease_phenotype_association_util.is_zero_frequency(frequency)


@pytest.mark.parametrize("frequency", ["0/0", "2/1", "-1/2", "101%", "NaN%", "0", "unknown", "HP:0001250"])
def test_invalid_frequency(frequency):
    with pytest.raises(ValueError, match="Invalid HPOA frequency"):
        disease_phenotype_association_util.is_zero_frequency(frequency)


def write_hpoa_rows(path, rows):
    header = "database_id\tdisease_name\tqualifier\thpo_id\treference\tevidence\tonset\tfrequency\tsex\tmodifier\taspect\tbiocuration\n"
    content = '#description: "Test annotations"\n#version: test\n' + header
    for database_id, hpo_id, qualifier, frequency in rows:
        content += "\t".join([database_id, "Disease", qualifier, hpo_id, "PMID:1", "PCS", "",
                              frequency, "", "", "P", "HPO:test"]) + "\n"
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize("prefix", ["OMIM", "ORPHA"])
@pytest.mark.parametrize("reverse", [False, True])
def test_filter_before_deduplication(tmp_path, prefix, reverse):
    rows = [
        (f"{prefix}:1", "HP:0000001", "NOT", ""),
        (f"{prefix}:2", "HP:0000001", "", "0/2"),
        (f"{prefix}:3", "HP:0000001", "", "0%"),
        (f"{prefix}:4", "HP:0000001", "", "HP:0040285"),
        (f"{prefix}:5", "HP:0000001", "", ""),
        (f"{prefix}:6", "HP:0000001", "NOT", "100%"),
        (f"{prefix}:6", "HP:0000001", "", "1/2"),
        (f"{prefix}:7", "HP:0000001", "", "0/2"),
        (f"{prefix}:7", "HP:0000001", "", "1/2"),
        (f"{prefix}:8", "HP:0000001", "", "HP:0040284"),
        (f" {prefix}:9 ", " HP:0000001 ", " ", " 1/2 "),
        (f"{prefix}:10", "HP:0000001", " NOT ", ""),
        (f"{prefix}:5", "HP:0000002", "NOT", ""),
        ("DECIPHER:1", "HP:0000001", "", ""),
    ]
    path = tmp_path / "patient's phenotype.hpoa"
    write_hpoa_rows(path, reversed(rows) if reverse else rows)
    actual = disease_phenotype_association_util.load_manual_phenotype_associations(path, prefix)
    assert actual == {f"{disease}\t0000001": "Manual" for disease in range(5, 10)}


@pytest.mark.parametrize("qualifier,frequency", [("UNKNOWN", ""), ("", "0/0"), ("", "garbage")])
def test_loader_rejects_invalid_annotations(tmp_path, qualifier, frequency):
    path = tmp_path / "phenotype.hpoa"
    write_hpoa_rows(path, [("OMIM:1", "HP:0000001", qualifier, frequency)])
    with pytest.raises(ValueError, match=r"OMIM:1 / HP:0000001"):
        disease_phenotype_association_util.load_manual_phenotype_associations(path, "OMIM")


def test_loader_preserves_hash_in_disease_name(tmp_path):
    path = tmp_path / "phenotype.hpoa"
    content = hpoa_content.replace(
        "Developmental and epileptic encephalopathy 96", "#111400 BLOOD GROUP, P1PK SYSTEM",
    )
    path.write_text(content, encoding="utf-8")
    actual = disease_phenotype_association_util.load_manual_phenotype_associations(path, "OMIM")
    assert len(actual) == 5
    assert "619340\t0011097" in actual


@pytest.mark.parametrize("column", ["qualifier", "frequency"])
def test_loader_requires_absence_columns(tmp_path, column):
    path = tmp_path / "phenotype.hpoa"
    columns = [name for name in ["database_id", "hpo_id", "qualifier", "frequency"] if name != column]
    row = {"database_id": "OMIM:1", "hpo_id": "HP:0000001", "qualifier": "NOT", "frequency": "0/2"}
    path.write_text("\t".join(columns) + "\n" + "\t".join(row[name] for name in columns) + "\n", encoding="utf-8")
    with pytest.raises(duckdb.Error):
        disease_phenotype_association_util.load_manual_phenotype_associations(path, "OMIM")


@pytest.mark.parametrize("reverse", [False, True])
def test_ordo_frequency_prefers_positive_duplicate(tmp_path, reverse):
    labels = ["Excluded (0%)", "Occasional (29-5%)"]
    if reverse:
        labels.reverse()
    records = "".join(
        f"<HPODisorderAssociation><HPO><HPOId>HP:0001250</HPOId></HPO>"
        f"<HPOFrequency><Name>{label}</Name></HPOFrequency></HPODisorderAssociation>"
        for label in labels
    )
    path = tmp_path / "product4.xml"
    path.write_text(
        f"<JDBOR><HPODisorderSetStatusList><Disorder><OrphaCode>1</OrphaCode>"
        f"<HPODisorderAssociationList>{records}</HPODisorderAssociationList>"
        f"</Disorder></HPODisorderSetStatusList></JDBOR>", encoding="utf-8",
    )
    assert disease_phenotype_association_util.load_ordo_frequency_annotations(path) == {
        "1\t0001250": "Occasional (29-5%)",
    }


def test_ordo_positive_hpoa_conflicting_frequency(tmp_path, caplog):
    util = disease_phenotype_association_util
    output = tmp_path / "Orphanet_HP_Association.ttl"
    util.write_ordo_phenotype_association_ttl(
        output, {"1\t0001250": "Manual"}, {"1\t0001250": "Excluded (0%)"},
        util.create_annotation_source(util.HPOA_SOURCE, "Orphanet", util.HPOA_PAGE),
    )
    graph = Graph().parse(output, format="turtle")
    assert len(list(graph.subjects(util.OA.hasBody, util.OBO.HP_0001250))) == 1
    assert not list(graph.triples((None, util.HOOM.with_frequency, util.OBO.HP_0040285)))
    assert "frequency conflicts with positive HPOA" in caplog.text


def test_issue_8_regression_through_both_build_steps(tmp_path, monkeypatch):
    from package import disease_phenotype_omim, disease_phenotype_ordo

    hpoa_path = tmp_path / "phenotype.hpoa"
    write_hpoa_rows(hpoa_path, [
        ("ORPHA:101112", "HP:0001250", "NOT", ""),
        ("ORPHA:52901", "HP:0000458", "NOT", ""),
        ("OMIM:228300", "HP:0004408", "", "0/2"),
        ("OMIM:146110", "HP:0004408", "", "0/2"),
        ("ORPHA:101112", "HP:0000001", "", ""),
        ("OMIM:228300", "HP:0000001", "", "1/2"),
        ("OMIM:1", "HP:0000001", "", "0/2"),
        ("OMIM:1", "HP:0000001", "", "1/2"),
    ])
    product4_path = tmp_path / "product4.xml"
    product4_path.write_text(product4_content, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.ini").write_text(
        "[Override]\nhpo_phenotype_path=phenotype.hpoa\n"
        "orphanet_product4_path=product4.xml\nrdf_output_dir=rdf\n", encoding="utf-8",
    )
    disease_phenotype_omim.disease_phenotype_omim()
    disease_phenotype_ordo.disease_phenotype_ordo()
    util = disease_phenotype_association_util
    omim = Graph().parse(tmp_path / "rdf/OMIM_HP_Association.ttl", format="turtle")
    orpha = Graph().parse(tmp_path / "rdf/Orphanet_HP_Association.ttl", format="turtle")
    assert not list(omim.subjects(util.OA.hasBody, util.OBO.HP_0004408))
    assert not list(orpha.subjects(util.OA.hasBody, util.OBO.HP_0001250))
    assert not list(orpha.subjects(util.OA.hasBody, util.OBO.HP_0000458))
    assert len(list(omim.subjects(util.OA.hasBody, util.OBO.HP_0000001))) == 2
    assert len(list(orpha.subjects(util.OA.hasBody, util.OBO.HP_0000001))) == 1
    assert len(list(omim.subjects(util.RDF.type, util.OA.Annotation))) == 2
    assert len(list(orpha.subjects(util.RDF.type, util.OA.Annotation))) == 1
