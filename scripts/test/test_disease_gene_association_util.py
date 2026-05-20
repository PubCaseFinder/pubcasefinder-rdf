from pathlib import Path
from rdflib import Graph, RDF, DCTERMS, Literal

from package import disease_gene_association_util

ncbi_content = """\
#tax_id	GeneID	Symbol	LocusTag	Synonyms	dbXrefs	chromosome	map_location	description	type_of_gene	Symbol_from_nomenclature_authority	Full_name_from_nomenclature_authority	Nomenclature_status	Other_designations	Modification_date	Feature_type
9606	1	A1BG	-	A1B|ABG|GAB|HYST2477	MIM:138670|HGNC:HGNC:5|Ensembl:ENSG00000121410|AllianceGenome:HGNC:5	19	19q13.43	alpha-1-B glycoprotein	protein-coding	A1BG	alpha-1-B glycoprotein	O	alpha-1B-glycoprotein|HEL-S-163pA|epididymis secretory sperm binding protein Li 163pA	20251125	-
9606	2	A2M	-	A2MD|CPAMD5|FWP007|S863-7	MIM:103950|HGNC:HGNC:7|Ensembl:ENSG00000175899|AllianceGenome:HGNC:7	12	12p13.31	alpha-2-macroglobulin	protein-coding	A2M	alpha-2-macroglobulin	O	alpha-2-macroglobulin|C3 and PZP-like alpha-2-macroglobulin domain-containing protein 5|alpha-2-M	20251125	-
9606	9	NAT1	-	AAC1|MNAT|NAT-1|NATI	MIM:108345|HGNC:HGNC:7645|Ensembl:ENSG00000171428|AllianceGenome:HGNC:7645	8	8p22	N-acetyltransferase 1	protein-coding	NAT1	N-acetyltransferase 1	O	arylamine N-acetyltransferase 1|N-acetyltransferase 1 (arylamine N-acetyltransferase)|N-acetyltransferase type 1|arylamide acetylase 1|monomorphic arylamine N-acetyltransferase	20251125	-
9606	10	NAT2	-	AAC2|NAT-2|PNAT	MIM:612182|HGNC:HGNC:7646|Ensembl:ENSG00000156006|AllianceGenome:HGNC:7646	8	8p22	N-acetyltransferase 2	protein-coding	NAT2	N-acetyltransferase 2	O	arylamine N-acetyltransferase 2|N-acetyltransferase 2 (arylamine N-acetyltransferase)|N-acetyltransferase type 2|N-hydroxyarylamine O-acetyltransferase|arylamide acetylase 2	20251125	-
9606	11	NATP	-	AACP|NATP1	HGNC:HGNC:15|AllianceGenome:HGNC:15	8	8p22	N-acetyltransferase pseudogene	pseudo	NATP	N-acetyltransferase pseudogene	O	arylamide acetylase pseudogene	20251125	-
"""

# 実データではなく、意図的にncbi_contentとgene_curieがマッチするように修正してある
hgnc_submission_content = """\
"uuid"	"gene_curie"	"gene_symbol"	"disease_curie"	"disease_title"	"disease_original_curie"	"disease_original_title"	"classification_curie"	"classification_title"	"moi_curie"	"moi_title"	"submitter_curie"	"submitter_title"	"submitted_as_hgnc_id"	"submitted_as_hgnc_symbol"	"submitted_as_disease_id"	"submitted_as_disease_name"	"submitted_as_moi_id"	"submitted_as_moi_name"	"submitted_as_submitter_id"	"submitted_as_submitter_name"	"submitted_as_classification_id"	"submitted_as_classification_name"	"submitted_as_date"	"submitted_as_public_report_url"	"submitted_as_notes"	"submitted_as_pmids"	"submitted_as_assertion_criteria_url"	"submitted_as_submission_id"	"submitted_run_date"
"GENCC_000101-HGNC_10896-OMIM_182212-HP_0000006-GENCC_100001"	"HGNC:5"	"SKI"	"MONDO:0008426"	"Shprintzen-Goldberg syndrome"	"OMIM:182212"	"Shprintzen-Goldberg syndrome"	"GENCC:100001"	"Definitive"	"HP:0000006"	"Autosomal dominant"	"GENCC:000101"	"Ambry Genetics"	"HGNC:10896"	"SKI"	"OMIM:182212"	"Shprintzen-Goldberg syndrome"	"HP:0000006"	"Autosomal dominant inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100001"	"Definitive"	"2018-03-30 13:31:56"	""	""	""	"PMID: 28106320"	"1034"	"2020-12-24"
"GENCC_000101-HGNC_16636-OMIM_171300-HP_0000006-GENCC_100003"	"HGNC:7"	"KIF1B"	"MONDO:0008233"	"pheochromocytoma"	"OMIM:171300"	"{Pheochromocytoma, susceptibility to}"	"GENCC:100003"	"Moderate"	"HP:0000006"	"Autosomal dominant"	"GENCC:000101"	"Ambry Genetics"	"HGNC:16636"	"KIF1B"	"OMIM:171300"	"Pheochromocytoma"	"HP:0000006"	"Autosomal dominant inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100003"	"Moderate"	"2019-12-04 13:30:43"	""	""	""	"PMID: 28106320"	"69237"	"2020-12-24"
"GENCC_000101-HGNC_16636-OMIM_118210-HP_0000006-GENCC_100004"	"HGNC:7645"	"KIF1B"	"MONDO:0007308"	"Charcot-Marie-Tooth disease type 2A1"	"OMIM:118210"	"Charcot-Marie-Tooth disease, type 2A1"	"GENCC:100004"	"Limited"	"HP:0000006"	"Autosomal dominant"	"GENCC:000101"	"Ambry Genetics"	"HGNC:16636"	"KIF1B"	"OMIM:118210"	"Charcot-Marie-Tooth disease, type 2A1"	"HP:0000006"	"Autosomal dominant inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100004"	"Limited"	"2024-10-15 12:08:25"	""	""	""	"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5655771/"	"61327"	"2025-01-17"
"GENCC_000101-HGNC_17939-OMIM_617532-HP_0000007-GENCC_100004"	"HGNC:15"	"SLC45A1"	"MONDO:0044322"	"intellectual developmental disorder with neuropsychiatric features"	"OMIM:617532"	"Intellectual developmental disorder with neuropsychiatric features"	"GENCC:100004"	"Limited"	"HP:0000007"	"Autosomal recessive"	"GENCC:000101"	"Ambry Genetics"	"HGNC:17939"	"SLC45A1"	"OMIM:617532"	"Intellectual developmental disorder with neuropsychiatric features"	"HP:0000007"	"Autosomal recessive inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100004"	"Limited"	"2024-09-26 12:08:38"	""	""	""	"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5655771/"	"17305"	"2025-01-17"
"""

mondo_owl_content = """\
<?xml version="1.0"?>
<rdf:RDF
    xmlns:owl="http://www.w3.org/2002/07/owl#"
    xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    xmlns:skos="http://www.w3.org/2004/02/skos/core#">
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_0008426">
        <skos:exactMatch rdf:resource="https://omim.org/entry/182212"/>
        <skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_2462"/>
        <skos:exactMatch rdf:resource="http://identifiers.org/mesh/D004194"/>
    </owl:Class>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_0008233">
        <skos:exactMatch rdf:resource="https://omim.org/entry/171300"/>
    </owl:Class>
    <owl:Class rdf:about="http://purl.obolibrary.org/obo/MONDO_9999999">
        <owl:deprecated rdf:datatype="http://www.w3.org/2001/XMLSchema#boolean">true</owl:deprecated>
        <skos:exactMatch rdf:resource="https://omim.org/entry/999999"/>
        <skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_999999"/>
    </owl:Class>
</rdf:RDF>
"""

mim2gen__medgen_content = """\
#MIM number	GeneID	type	Source	MedGenCUI	Comment
100050	-	phenotype	-	C3149220	-
100070	-	phenotype	-	C1853365	-
100100	1131	phenotype	 GeneMap	C0033770	-
100200	-	phenotype	-	C4551519	-
100300	57514	phenotype	 GeneMap	C4551482	-
100600	-	phenotype	-	C2930792	-
100640	216	gene	-	-	-
"""

def mock_load_hgnc_to_ncbi_map(_path):
    return {
        '5': '1',
        '7': '2',
        '7645': '9',
        '7646': '10',
        '15': '11'
    }

def mock_load_mondo_mapping_from_owl(_path):
    return disease_gene_association_util.MondoMapping(
        mondo_to_omim = {
            '0008426': ['182212'],
            '0008233': ['171300'],
        },
        mondo_to_orpha = {
            '0008426': ['2462'],
        },
        omim_to_mondo = {
            '182212': ['0008426'],
            '171300': ['0008233'],
        },
        orpha_to_mondo = {
            '2462': ['0008426'],
        }
    )


def create_mock_file(path: str, content: str):
    source_path = Path(path)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.touch()
    source_path.write_text(content)

def test_load_hgnc_to_ncbi_map(tmp_path):
    ncbi_file_path = (tmp_path / 'Homo_sapiens.gene_info').as_posix()
    create_mock_file(ncbi_file_path, ncbi_content)

    hgnc_to_ncbi_map = disease_gene_association_util.load_hgnc_to_ncbi_map(ncbi_file_path)

    expect_hgnc_to_ncbi_map = {
        '5': '1',
        '7': '2',
        '7645': '9',
        '7646': '10',
        '15': '11'
    }

    assert hgnc_to_ncbi_map == expect_hgnc_to_ncbi_map

def test_load_gencc_submission_records(mocker, tmp_path):
    ncbi_file_path = (tmp_path / 'Homo_sapiens.gene_info').as_posix()
    hgnc_submission_path = (tmp_path / 'gencc-submissions.tsv').as_posix()
    create_mock_file(hgnc_submission_path, hgnc_submission_content)

    mocker.patch.object(disease_gene_association_util, 'load_hgnc_to_ncbi_map', mock_load_hgnc_to_ncbi_map)
    records = disease_gene_association_util.load_gencc_submission_records(hgnc_submission_path, ncbi_file_path)

    expect_records = [
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:182212/gene:ENT:1'
            ],
            disease_uri=disease_gene_association_util.MIM['182212'],
            gene_uri=disease_gene_association_util.NCBIGENE['1'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_10896-OMIM_182212-HP_0000006-GENCC_100001'
            ],
            classification_title='Definitive',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000006'],
            submitter_label='Ambry Genetics',
        ),
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:171300/gene:ENT:2'
            ],
            disease_uri=disease_gene_association_util.MIM['171300'],
            gene_uri=disease_gene_association_util.NCBIGENE['2'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_16636-OMIM_171300-HP_0000006-GENCC_100003'
            ],
            classification_title='Moderate',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000006'],
            submitter_label='Ambry Genetics',
        ),
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:118210/gene:ENT:9'
            ],
            disease_uri=disease_gene_association_util.MIM['118210'],
            gene_uri=disease_gene_association_util.NCBIGENE['9'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_16636-OMIM_118210-HP_0000006-GENCC_100004'
            ],
            classification_title='Limited',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000006'],
            submitter_label='Ambry Genetics',
        ),
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:617532/gene:ENT:11'
            ],
            disease_uri=disease_gene_association_util.MIM['617532'],
            gene_uri=disease_gene_association_util.NCBIGENE['11'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_17939-OMIM_617532-HP_0000007-GENCC_100004'
            ],
            classification_title='Limited',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000007'],
            submitter_label='Ambry Genetics',
        ),
    ]

    assert records == expect_records

def test_load_gencc_associations(mocker, tmp_path):
    ncbigene_gene_info_path = (tmp_path / 'Homo_sapiens.gene_info').as_posix()
    mondo_owl_path = (tmp_path / 'mondo-international.owl').as_posix()
    gencc_submissions_path = (tmp_path / 'gencc-submissions.tsv').as_posix()

    mocker.patch.object(disease_gene_association_util, 'load_hgnc_to_ncbi_map', mock_load_hgnc_to_ncbi_map)
    mocker.patch.object(disease_gene_association_util, 'load_mondo_mapping_from_owl', mock_load_mondo_mapping_from_owl)

    create_mock_file(ncbigene_gene_info_path, '')
    create_mock_file(mondo_owl_path, '')
    create_mock_file(gencc_submissions_path, hgnc_submission_content)

    associations = disease_gene_association_util.load_gencc_associations(
        ncbigene_gene_info_path,
        mondo_owl_path,
        gencc_submissions_path,
        {"GENCC:100001"},
        project_mondo_to_mapped_diseases=True
    )

    print(associations)
    assert associations.omim_associations == {
        '182212\t1': ['GenCC'],
    }
    assert associations.orphanet_associations == {
        '2462\t1': ['GenCC'],
    }
    assert associations.mondo_associations == {
        '0008426\t1': ['GenCC'],
    }

def test_load_omim_gene_associations(tmp_path):
    mim2gen__medgen_path = (tmp_path / 'mim2gene_medgen.txt').as_posix()
    create_mock_file(mim2gen__medgen_path, mim2gen__medgen_content)
    associations = disease_gene_association_util.load_omim_gene_associations(mim2gen__medgen_path)
    expect_associations = {
        '100100\t1131': ['MedGen'],
        '100300\t57514': ['MedGen'],
    }
    assert associations == expect_associations

def test_add_original_disease_association():
    associations = disease_gene_association_util.GenCCAssociations()
    cases = [
        {
            'ncbi_id': '2103',
            'original_disease_curie': 'OMIM:608565',
        },
        {
            'ncbi_id': '83636',
            'original_disease_curie': 'Orphanet:289560',
        },
        {
            'ncbi_id': '652',
            'original_disease_curie': 'MONDO:0100613',
        }
    ]
    for case in cases:
        disease_gene_association_util.add_original_disease_association(
            associations,
            case['ncbi_id'],
            case['original_disease_curie']
        )

    assert associations.mondo_associations == {
        '0100613\t652': ['GenCC'],
    }
    assert associations.omim_associations == {
        '608565\t2103': ['GenCC'],
    }
    assert associations.orphanet_associations == {
        '289560\t83636': ['GenCC'],
    }

def test_load_mondo_mapping_from_owl(tmp_path):
    mondo_owl_path = (tmp_path / 'mondo-international.owl').as_posix()
    create_mock_file(mondo_owl_path, mondo_owl_content)

    mapping = disease_gene_association_util.load_mondo_mapping_from_owl(mondo_owl_path)

    assert mapping.mondo_to_omim == {
        '0008426': ['182212'],
        '0008233': ['171300'],
    }
    assert mapping.mondo_to_orpha == {
        '0008426': ['2462'],
    }
    assert mapping.omim_to_mondo == {
        '182212': ['0008426'],
        '171300': ['0008233'],
    }
    assert mapping.orpha_to_mondo == {
        '2462': ['0008426'],
    }

def test_write_gencc_gene_association_ttl(tmp_path):
    output_path = Path(tmp_path)
    output_path.mkdir(parents=True, exist_ok=True)
    mock_records = [
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:182212/gene:ENT:1'
            ],
            disease_uri=disease_gene_association_util.MIM['182212'],
            gene_uri=disease_gene_association_util.NCBIGENE['1'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_10896-OMIM_182212-HP_0000006-GENCC_100001'
            ],
            classification_title='Definitive',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000006'],
            submitter_label='Ambry Genetics',
        ),
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:171300/gene:ENT:2'
            ],
            disease_uri=disease_gene_association_util.MIM['171300'],
            gene_uri=disease_gene_association_util.NCBIGENE['2'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_16636-OMIM_171300-HP_0000006-GENCC_100003'
            ],
            classification_title='Moderate',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000006'],
            submitter_label='Ambry Genetics',
        ),
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:118210/gene:ENT:9'
            ],
            disease_uri=disease_gene_association_util.MIM['118210'],
            gene_uri=disease_gene_association_util.NCBIGENE['9'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_16636-OMIM_118210-HP_0000006-GENCC_100004'
            ],
            classification_title='Limited',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000006'],
            submitter_label='Ambry Genetics',
        ),
        disease_gene_association_util.GenCCSubmissionRecord(
            association_uri=disease_gene_association_util.GENE_CONTEXT[
                'disease:OMIM:617532/gene:ENT:11'
            ],
            disease_uri=disease_gene_association_util.MIM['617532'],
            gene_uri=disease_gene_association_util.NCBIGENE['11'],
            submission_uri=disease_gene_association_util.GENCC[
                'GENCC_000101-HGNC_17939-OMIM_617532-HP_0000007-GENCC_100004'
            ],
            classification_title='Limited',
            inheritance_uri=disease_gene_association_util.OBO['HP_0000007'],
            submitter_label='Ambry Genetics',
        ),
    ]
    output_path = Path((output_path / 'GenCC_Gene_Association.ttl').as_posix())
    disease_gene_association_util.write_gencc_gene_association_ttl(
        output_path,
        mock_records
    )

    expect_rdf_map = {
        RDF.type: [disease_gene_association_util.SIO["SIO_000983"]],
        disease_gene_association_util.SIO["SIO_000628"]: [ disease_gene_association_util.MIM['171300'], disease_gene_association_util.NCBIGENE['2']],
        DCTERMS.source: [disease_gene_association_util.GENCC['GENCC_000101-HGNC_16636-OMIM_171300-HP_0000006-GENCC_100003']],
        disease_gene_association_util.OBO["IAO_0000114"]: [Literal('Moderate')]
    }

    g = Graph()
    g.parse(output_path, format='turtle')
    query_statement = """
PREFIX sio: <http://semanticscience.org/resource/>
select ?p ?o
where {
    <https://pubcasefinder.dbcls.jp/gene_context/disease:OMIM:171300/gene:ENT:2> ?p ?o .
}
"""

    rows = g.query(query_statement)

    for row in rows:
        key = row[0]
        value = row[1]

        assert value in expect_rdf_map[key]

def test_extract_mondo_id_from_uri():
    mock_uri = '    <!-- http://purl.obolibrary.org/obo/MONDO_8000034 -->'
    result = disease_gene_association_util.extract_mondo_id_from_uri(mock_uri)
    assert result == '8000034'

def test_extract_omim_id():
    mock_uri = '<skos:exactMatch rdf:resource="https://omim.org/entry/607948"/>'
    result = disease_gene_association_util.extract_omim_id(mock_uri)
    assert result == '607948'

def test_extract_orphanet_id():
    mock_uri = '<skos:exactMatch rdf:resource="http://www.orpha.net/ORDO/Orphanet_377788"/>'
    result = disease_gene_association_util.extract_orphanet_id(mock_uri)
    assert result == '377788'


