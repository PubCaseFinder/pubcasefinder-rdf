from rdflib import Graph, BNode
from rdflib.compare import isomorphic, to_isomorphic, graph_diff

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


def test_write_manual_phenotype_association_ttl_matches_legacy_graph(tmp_path):
    output_path = tmp_path / "OMIM_HP_Association.ttl"
    source = disease_phenotype_association_util.create_annotation_source(
        "Human Phenotype Ontology Consortium",
        disease_phenotype_association_util.HPOA_SOURCE_URI,
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
PREFIX mim: <https://omim.org/entry/>
PREFIX oa: <http://www.w3.org/ns/oa#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:OMIM:619340/phenotype:HP:0011097>
    a oa:Annotation ;
    oa:hasTarget mim:619340 ;
    oa:hasBody obo:HP_0011097 ;
    dcterms:source _:b1 ;
    obo:ECO_9000001 obo:ECO_0000218 .

_:b1
    dcterms:creator "{source.creator}" ;
    foaf:page <{source.page}> .

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:OMIM:619340/phenotype:HP:0002187>
    a oa:Annotation ;
    oa:hasTarget mim:619340 ;
    oa:hasBody obo:HP_0002187 ;
    dcterms:source _:b2 ;
    obo:ECO_9000001 obo:ECO_0000218 .

_:b2
    dcterms:creator "{source.creator}" ;
    foaf:page <{source.page}> .
""",
        format="turtle"
    )

    assert len(actual_graph) == 14
    assert isomorphic(actual_graph, expect_graph)


def test_write_ordo_phenotype_association_ttl_matches_legacy_graph(tmp_path):
    output_path = tmp_path / "Orphanet_HP_Association.ttl"
    source = disease_phenotype_association_util.create_annotation_source(
        "Orphanet",
        disease_phenotype_association_util.HPOA_SOURCE_URI,
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
    dcterms:source _:b1 ;
    obo:ECO_9000001 obo:ECO_0000218 .

_:b1
    dcterms:creator "{source.creator}" ;
    foaf:page <{source.page}> .

<https://pubcasefinder.dbcls.jp/phenotype_context/disease:ORDO:166024/phenotype:HP:0011097>
    a oa:Annotation ;
    oa:hasTarget ordo:Orphanet_166024 ;
    oa:hasBody obo:HP_0011097 ;
    dcterms:source _:b2 ;
    obo:ECO_9000001 obo:ECO_0000218 .

_:b2
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

    assert len(actual_graph) == 21
    assert isomorphic(actual_graph, expect_graph)
