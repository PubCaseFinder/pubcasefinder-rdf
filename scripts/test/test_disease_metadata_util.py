from pathlib import Path
from rdflib import Graph, RDF, DCTERMS, Literal, URIRef

from package import disease_metadata_util
from test.test_disease_gene_association_util import create_mock_file

mim2gene_content = """
# Copyright (c) 1966-2026 Johns Hopkins University. Use of this file adheres to the terms specified at https://omim.org/help/agreement
# Generated: 2026-02-02
# This file provides links between the genes in OMIM and other gene identifiers.
# THIS IS NOT A TABLE OF GENE-PHENOTYPE RELATIONSHIPS.
# MIM Number	MIM Entry Type (see FAQ 1.3 at https://omim.org/help/faq)	Entrez Gene ID (NCBI)	Approved Gene Symbol (HGNC)	Ensembl Gene ID (Ensembl)
100050	predominantly phenotypes			
100070	phenotype	100329167		
100100	phenotype			
100200	predominantly phenotypes			
100300	phenotype			
100500	moved/removed			
100600	phenotype			
100640	gene	216	ALDH1A1	ENSG00000165092
100650	gene	217	ALDH2	ENSG00000111275
"""

medgene_omim_hpo_content = """
#OMIM_CUI|MIM_number|OMIM_name|relationship|HPO_CUI|HPO_ID|HPO_name|MedGen_name|MedGen_source|STY|
C0432273|144750|ENDOSTEAL HYPEROSTOSIS, AUTOSOMAL DOMINANT|manifestation_of|C4025901|HP:0000002|Abnormality of body height|Abnormality of body height|GTR|Finding|
C1861305|186570|TARSAL-CARPAL COALITION SYNDROME|manifestation_of|C4025901|HP:0000002|Abnormality of body height|Abnormality of body height|GTR|Finding|
C2675891|612475|CHROMOSOME 1q21.1 DUPLICATION SYNDROME|manifestation_of|C4025901|HP:0000002|Abnormality of body height|Abnormality of body height|GTR|Finding|
C4540488|617800|MICROCEPHALY 19, PRIMARY, AUTOSOMAL RECESSIVE|manifestation_of|C4025901|HP:0000002|Abnormality of body height|Abnormality of body height|GTR|Finding|
C5975613|621091|OCULAR PTERYGIUM-DIGITAL KELOID DYSPLASIA SYNDROME|manifestation_of|C4025901|HP:0000002|Abnormality of body height|Abnormality of body height|GTR|Finding|
C0001080|100800|ACHONDROPLASIA|inheritance_type_of|C0443147|HP:0000006|Autosomal dominant inheritance|Autosomal dominant inheritance|GTR|Genetic Function|
C0001080|100800|ACHONDROPLASIA|inheritance_type_of|C0443147|HP:0000006|Autosomal dominant inheritance|Autosomal dominant inheritance|GTR|Intellectual Product|
"""

mondo_owl_content = """\
<?xml version="1.0"?>
<rdf:RDF
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#">
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_0000001">
        <skos:exactMatch rdf:resource="https://omim.org/entry/100100"/>
        <skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_123"/>
        <skos:exactMatch rdf:resource="http://linkedlifedata.com/resource/umls/id/C0000001"/>
    </owl:Class>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_0000002">
        <skos:exactMatch rdf:resource="http://identifiers.org/omim/100200"/>
    </owl:Class>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_9999999">
        <owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</owl:deprecated>
        <skos:exactMatch rdf:resource="https://omim.org/entry/999999"/>
        <skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_999"/>
    </owl:Class>
</rdf:RDF>
"""

mondo_owl_orhanet_content = """\
<?xml version="1.0"?>
<rdf:RDF xmlns="http://purl.obolibrary.org/obo/mondo/mondo-international.owl#"
     xml:base="http://purl.obolibrary.org/obo/mondo/mondo-international.owl"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:obo="http://purl.obolibrary.org/obo/"
     xmlns:owl="http://www.w3.org/2002/07/owl#"
     xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
     xmlns:xml="http://www.w3.org/XML/1998/namespace"
     xmlns:xsd="http://www.w3.org/2001/XMLSchema#"
     xmlns:doap="http://usefulinc.com/ns/doap#"
     xmlns:foaf="http://xmlns.com/foaf/0.1/"
     xmlns:rdfs="http://www.w3.org/2000/01/rdf-schema#"
     xmlns:skos="http://www.w3.org/2004/02/skos/core#"
     xmlns:mondo="http://purl.obolibrary.org/obo/mondo#"
     xmlns:sssom="https://w3id.org/sssom/"
     xmlns:terms="http://purl.org/dc/terms/"
     xmlns:vocab="https://w3id.org/semapv/vocab/"
     xmlns:babelon="https://w3id.org/babelon/"
     xmlns:protege="http://protege.stanford.edu/plugins/owl/protege#"
     xmlns:oboInOwl="http://www.geneontology.org/formats/oboInOwl#">
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_0000001">
        <skos:exactMatch rdf:resource="https://omim.org/entry/100100"/>
        <skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_123"/>
        <skos:exactMatch rdf:resource="http://linkedlifedata.com/resource/umls/id/C0000001"/>
    </owl:Class>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_0000107">
        <rdfs:subClassOf rdf:resource="http://purl.obolibrary.org/obo/MONDO_0007500"/>
        <obo:IAO_0000115>Auriculo-condylar syndrome (ACS) presents with bilateral external ear malformations (&apos;question mark&apos; ears), mandibular condyle hypoplasia, microstomia, micrognathia, microglossia and facial asymmetry. Additional manifestations include hypotonia, ptosis, cleft palate, puffy cheeks, developmental delay, impaired hearing and respiratory distress.</obo:IAO_0000115>
        <mondo:curated_content_resource rdf:datatype="http://www.w3.org/2001/XMLSchema#anyURI">https://www.malacards.org/card/auriculocondylar_syndrome</mondo:curated_content_resource>
        <mondo:excluded_from_qc_check rdf:resource="http://purl.obolibrary.org/obo/mondo/sparql/qc/general/qc-single-child.sparql"/>
        <mondo:excluded_subClassOf rdf:resource="http://purl.obolibrary.org/obo/MONDO_0015397"/>
        <mondo:should_conform_to rdf:resource="http://purl.obolibrary.org/obo/mondo/patterns/OMIM_phenotypic_series.yaml"/>
        <oboInOwl:hasDbXref>GARD:0009798</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>MEDGEN:355953</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>MESH:C538270</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>OMIMPS:602483</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>Orphanet:137888</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>SCTID:702443003</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>UMLS:C1865295</oboInOwl:hasDbXref>
        <oboInOwl:hasDbXref>icd11.foundation:1545895796</oboInOwl:hasDbXref>
        <oboInOwl:hasExactSynonym>auriculo-condylar syndrome</oboInOwl:hasExactSynonym>
        <oboInOwl:hasExactSynonym>question mark ear syndrome</oboInOwl:hasExactSynonym>
        <oboInOwl:hasRelatedSynonym>dysgnathia complex</oboInOwl:hasRelatedSynonym>
        <oboInOwl:hasRelatedSynonym>ears prominent and constricted</oboInOwl:hasRelatedSynonym>
        <oboInOwl:hasRelatedSynonym>question mark ear</oboInOwl:hasRelatedSynonym>
        <oboInOwl:hasRelatedSynonym>question-mark ear syndrome</oboInOwl:hasRelatedSynonym>
        <oboInOwl:id>MONDO:0000107</oboInOwl:id>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#gard_rare"/>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#nord_rare"/>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#ordo_disorder"/>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#ordo_malformation_syndrome"/>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#orphanet_rare"/>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#otar"/>
        <oboInOwl:inSubset rdf:resource="http://purl.obolibrary.org/obo/mondo#rare"/>
        <rdfs:label>auriculocondylar syndrome</rdfs:label>
        <rdfs:label xml:lang="ja">耳下顎関節頭症候群</rdfs:label>
        <skos:exactMatch rdf:resource="http://id.who.int/icd/entity/1545895796"/>
        <skos:exactMatch rdf:resource="http://identifiers.org/medgen/355953"/>
        <skos:exactMatch rdf:resource="http://identifiers.org/mesh/C538270"/>
        <skos:exactMatch rdf:resource="http://identifiers.org/snomedct/702443003"/>
        <skos:exactMatch rdf:resource="http://linkedlifedata.com/resource/umls/id/C1865295"/>
        <skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_137888"/>
        <skos:exactMatch rdf:resource="https://omim.org/phenotypicSeries/PS602483"/>
    </owl:Class>
</rdf:RDF>
"""

mondo_obo_content = """\
format-version: 1.2

[Term]
id: MONDO:0000001
xref: OMIM:100100 {source="MONDO:equivalentTo"}
xref: Orphanet:123 {source="MONDO:equivalentTo"}
xref: UMLS:C0000001 {source="MONDO:equivalentTo"}

[Term]
id: MONDO:0000002
xref: OMIM:100200 {source="MONDO:equivalentTo"}
xref: OMIMPS:602483 {source="MONDO:equivalentTo"}
xref: Orphanet:456 {source="MONDO:relatedTo"}

[Term]
id: MONDO:9999999
is_obsolete: true
xref: OMIM:999999 {source="MONDO:equivalentTo"}
xref: Orphanet:999 {source="MONDO:equivalentTo"}
"""

def test_load_omim_disease_ids(tmp_path):
    mim2gene_path = (tmp_path / 'mim2gene.txt').as_posix()
    create_mock_file(mim2gene_path, mim2gene_content)
    omim_ids = disease_metadata_util.load_omim_disease_ids(mim2gene_path)
    expect_omim_ids = [
        '100050',
        '100070',
        '100100',
        '100200',
        '100300',
        '100600',
    ]
    assert omim_ids == expect_omim_ids

def test_load_omim_inheritance_map(tmp_path):
    medgene_omim_hpo_path = (tmp_path / 'MedGen_HPO_OMIM_Mapping.txt').as_posix()
    create_mock_file(medgene_omim_hpo_path, medgene_omim_hpo_content)
    inheritance_map = disease_metadata_util.load_omim_inheritance_map(medgene_omim_hpo_path)
    expect_inheritance_map = {
        '100800': ['0000006'],
        '100800': ['0000006'],
    }
    assert inheritance_map == expect_inheritance_map

def test_load_disease_mappings_from_owl_orphanet(tmp_path):
    mondo_owl_path = (tmp_path / 'mondo.owl').as_posix()
    create_mock_file(mondo_owl_path, mondo_owl_orhanet_content)
    mappings = disease_metadata_util.load_disease_mappings_from_owl(mondo_owl_path)
    expect_mappings = disease_metadata_util.DiseaseMappings(
        omim_to_mondo = {
            '100100': ['0000001']
        },
        omim_to_umls = {
            '100100': ['C0000001']
        },
        orphanet_to_mondo = {
            '123': '0000001',
            '137888': '0000107'
        },
        orphanet_to_omim = {
            '123': '100100'
        },
        orphanet_to_umls = {
            '123': ['C0000001'],
            '137888': ['C1865295']
        },
        orphanet_ids = [
            '123',
            '137888'
        ]
    )
    assert mappings.omim_to_mondo == expect_mappings.omim_to_mondo
    assert mappings.omim_to_umls == expect_mappings.omim_to_umls
    assert mappings.orphanet_to_mondo == expect_mappings.orphanet_to_mondo
    assert mappings.orphanet_to_omim == expect_mappings.orphanet_to_omim
    assert mappings.orphanet_to_umls == expect_mappings.orphanet_to_umls
    assert mappings.orphanet_ids == expect_mappings.orphanet_ids

def test_iter_mondo_exact_matches_from_owl(tmp_path):
    mondo_owl_path = (tmp_path / 'mondo.owl').as_posix()
    create_mock_file(mondo_owl_path, mondo_owl_content)
    mondo_list = disease_metadata_util.iter_mondo_exact_matches_from_owl(mondo_owl_path)
    def create_expect_mondo_list():
        pre_expect_mondo_list = [
            {
                'mondo_id': '0000001',
                'exact_matches': [
                    'http://linkedlifedata.com/resource/umls/id/C0000001',
                    'http://www.orpha.net/ORDO/Orphanet_123',
                    'https://omim.org/entry/100100',
                ],
                'obsolete': False
            },
            {
                'mondo_id': '0000002',
                'exact_matches': [
                    'http://identifiers.org/omim/100200',
                ],
                'obsolete': False
            },
            {
                'mondo_id': '9999999',
                'exact_matches': [
                    'http://www.orpha.net/ORDO/Orphanet_999',
                    'https://omim.org/entry/999999',
                ],
                'obsolete': True
            },
        ]
        for pre_expect_mondo in pre_expect_mondo_list:
            yield disease_metadata_util.MondoExactMatches(
                mondo_id=pre_expect_mondo['mondo_id'],
                exact_matches=pre_expect_mondo['exact_matches'],
                obsolete=pre_expect_mondo['obsolete']
            )
    expect_mondo_list = create_expect_mondo_list()
    assert list(mondo_list) == list(expect_mondo_list)

def test_iter_mondo_exact_matches_from_obo(tmp_path):
    mondo_owl_path = (tmp_path / 'mondo.obo').as_posix()
    create_mock_file(mondo_owl_path, mondo_obo_content)
    mondo_list = disease_metadata_util.iter_mondo_exact_matches_from_obo(mondo_owl_path)
    def create_expect_mondo_list():
        pre_expect_mondo_list = [
            {
                'mondo_id': '0000001',
                'exact_matches': [
                    'OMIM:100100',
                    'Orphanet:123',
                    'UMLS:C0000001',
                ],
                'obsolete': False
            },
            {
                'mondo_id': '0000002',
                'exact_matches': [
                    'OMIM:100200',
                    'OMIMPS:602483',
                ],
                'obsolete': False
            },
            {
                'mondo_id': '9999999',
                'exact_matches': [
                    'OMIM:999999',
                    'Orphanet:999',
                ],
                'obsolete': True
            },
        ]
        for pre_expect_mondo in pre_expect_mondo_list:
            yield disease_metadata_util.MondoExactMatches(
                mondo_id=pre_expect_mondo['mondo_id'],
                exact_matches=pre_expect_mondo['exact_matches'],
                obsolete=pre_expect_mondo['obsolete']
            )
    expect_mondo_list = create_expect_mondo_list()
    assert list(mondo_list) == list(expect_mondo_list)

def assert_basic_disease_mappings(mappings):
    expect_mappings = disease_metadata_util.DiseaseMappings(
        omim_to_mondo = {
            '100100': ['0000001'],
            '100200': ['0000002'],
        },
        omim_to_umls = {
            '100100': ['C0000001'],
        },
        orphanet_to_mondo = {
            '123': '0000001',
        },
        orphanet_to_omim = {
            '123': '100100',
        },
        orphanet_to_umls = {
            '123': ['C0000001'],
        },
        orphanet_ids = [
            '123',
        ]
    )
    assert mappings.omim_to_mondo == expect_mappings.omim_to_mondo
    assert mappings.omim_to_umls == expect_mappings.omim_to_umls
    assert mappings.orphanet_to_mondo == expect_mappings.orphanet_to_mondo
    assert mappings.orphanet_to_omim == expect_mappings.orphanet_to_omim
    assert mappings.orphanet_to_umls == expect_mappings.orphanet_to_umls
    assert mappings.orphanet_ids == expect_mappings.orphanet_ids

def test_build_disease_mappings_from_obo_iterator(tmp_path):
    mondo_obo_path = (tmp_path / 'mondo.obo').as_posix()
    create_mock_file(mondo_obo_path, mondo_obo_content)

    mappings = disease_metadata_util.build_disease_mappings(
        disease_metadata_util.iter_mondo_exact_matches_from_obo(mondo_obo_path)
    )

    assert_basic_disease_mappings(mappings)

def test_build_disease_mappings_from_owl_iterator(tmp_path):
    mondo_owl_path = (tmp_path / 'mondo.owl').as_posix()
    create_mock_file(mondo_owl_path, mondo_owl_content)

    mappings = disease_metadata_util.build_disease_mappings(
        disease_metadata_util.iter_mondo_exact_matches_from_owl(mondo_owl_path)
    )

    assert_basic_disease_mappings(mappings)

def test_finalize_mondo_term():
    mappings = disease_metadata_util.DiseaseMappings()
    mock_data_list = [
        {
            'mondo_id': '0000001',
            'omim_ids': ['100100'],
            'orphanet_ids': ['123'],
            'umls_ids': ['C0000001']
        },
        {
            'mondo_id': '0000107',
            'omim_ids': [],
            'orphanet_ids': ['137888'],
            'umls_ids': ['C1865295']
        }
    ]
    for mock_data in mock_data_list:
        disease_metadata_util.finalize_mondo_term(
            mappings,
            mock_data['mondo_id'],
            mock_data['omim_ids'],
            mock_data['orphanet_ids'],
            mock_data['umls_ids'],
            obsolete=False,
        )
    expect_mappings = disease_metadata_util.DiseaseMappings(
        omim_to_mondo = {
            '100100': ['0000001']
        },
        omim_to_umls = {
            '100100': ['C0000001']
        },
        orphanet_to_mondo = {
            '123': '0000001',
            '137888': '0000107'
        },
        orphanet_to_omim = {
            '123': '100100'
        },
        orphanet_to_umls = {
            '123': ['C0000001'],
            '137888': ['C1865295']
        },
        orphanet_ids = [
            '123',
            '137888'
        ]
    )
    assert mappings.omim_to_mondo == expect_mappings.omim_to_mondo
    assert mappings.omim_to_umls == expect_mappings.omim_to_umls
    assert mappings.orphanet_to_mondo == expect_mappings.orphanet_to_mondo
    assert mappings.orphanet_to_omim == expect_mappings.orphanet_to_omim
    assert mappings.orphanet_to_umls == expect_mappings.orphanet_to_umls
    assert mappings.orphanet_ids == expect_mappings.orphanet_ids

def test_load_kegg_map(tmp_path):
    kegg_path = tmp_path / 'kegg.tsv'
    kegg_content = """
100100	H02129
100300	H01413
100800	H00505
100800	H01749
"""
    create_mock_file(kegg_path, kegg_content)
    kegg_map = disease_metadata_util.load_kegg_map(kegg_path)
    expect_kegg_map = {
        '100100': 'H02129',
        '100300': 'H01413',
        '100800': 'H00505',
        '100800': 'H01749',
    }
    assert kegg_map == expect_kegg_map

def test_load_gene_reviews_map(tmp_path):
    gene_reviews_path = tmp_path / 'NBKid_shortname_OMIM.txt'
    gene_reviews_content = """\
#NBK_id	GR_shortname	OMIM
NBK1103	trimethylaminuria	136132
NBK1103	trimethylaminuria	602079
NBK1104	cdls	122470
NBK1105	cdls2	122470
NBK1105	cdls2	122470
"""
    create_mock_file(gene_reviews_path, gene_reviews_content)

    gene_reviews_map = disease_metadata_util.load_gene_reviews_map(gene_reviews_path)

    expect_gene_reviews_map = {
        '136132': ['NBK1103'],
        '602079': ['NBK1103'],
        '122470': ['NBK1104', 'NBK1105'],
    }
    assert gene_reviews_map == expect_gene_reviews_map
