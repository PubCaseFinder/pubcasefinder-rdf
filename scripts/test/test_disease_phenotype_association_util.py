from pathlib import Path
from rdflib import Graph, RDF, DCTERMS, Literal, URIRef

from package import disease_phenotype_association_util
from test.test_disease_gene_association_util import create_mock_file

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

def test_load_manual_phenotype_associations(tmp_path):
    hpoa_path = tmp_path / 'phenotype.hpoa'
    create_mock_file(hpoa_path, hpoa_content)
    manual_association_map = disease_phenotype_association_util.load_manual_phenotype_associations(hpoa_path, 'OMIM')
    expect_manual_association_map = {
        '619340\t0011097': 'Manual',
        '619340\t0002187': 'Manual',
        '619340\t0001518': 'Manual',
        '619340\t0032792': 'Manual',
        '619340\t0011451': 'Manual',
    }

    assert manual_association_map == expect_manual_association_map