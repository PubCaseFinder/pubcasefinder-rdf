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