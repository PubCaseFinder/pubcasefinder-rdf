from pathlib import Path

import pytest
from package import disease_gene_association_util

def create_mock_file(path: str, content: str):
    source_path = Path(path)
    source_path.parent.mkdir(parents=True, exist_ok=True)
    source_path.touch()
    source_path.write_text(content)

def test_load_hgnc_to_ncbi_map(tmp_path):
    ncbi_file_path = (tmp_path / 'Homo_sapiens.gene_info').as_posix()
    ncbi_content = """\
#tax_id	GeneID	Symbol	LocusTag	Synonyms	dbXrefs	chromosome	map_location	description	type_of_gene	Symbol_from_nomenclature_authority	Full_name_from_nomenclature_authority	Nomenclature_status	Other_designations	Modification_date	Feature_type
9606	1	A1BG	-	A1B|ABG|GAB|HYST2477	MIM:138670|HGNC:HGNC:5|Ensembl:ENSG00000121410|AllianceGenome:HGNC:5	19	19q13.43	alpha-1-B glycoprotein	protein-coding	A1BG	alpha-1-B glycoprotein	O	alpha-1B-glycoprotein|HEL-S-163pA|epididymis secretory sperm binding protein Li 163pA	20251125	-
9606	2	A2M	-	A2MD|CPAMD5|FWP007|S863-7	MIM:103950|HGNC:HGNC:7|Ensembl:ENSG00000175899|AllianceGenome:HGNC:7	12	12p13.31	alpha-2-macroglobulin	protein-coding	A2M	alpha-2-macroglobulin	O	alpha-2-macroglobulin|C3 and PZP-like alpha-2-macroglobulin domain-containing protein 5|alpha-2-M	20251125	-
9606	9	NAT1	-	AAC1|MNAT|NAT-1|NATI	MIM:108345|HGNC:HGNC:7645|Ensembl:ENSG00000171428|AllianceGenome:HGNC:7645	8	8p22	N-acetyltransferase 1	protein-coding	NAT1	N-acetyltransferase 1	O	arylamine N-acetyltransferase 1|N-acetyltransferase 1 (arylamine N-acetyltransferase)|N-acetyltransferase type 1|arylamide acetylase 1|monomorphic arylamine N-acetyltransferase	20251125	-
9606	10	NAT2	-	AAC2|NAT-2|PNAT	MIM:612182|HGNC:HGNC:7646|Ensembl:ENSG00000156006|AllianceGenome:HGNC:7646	8	8p22	N-acetyltransferase 2	protein-coding	NAT2	N-acetyltransferase 2	O	arylamine N-acetyltransferase 2|N-acetyltransferase 2 (arylamine N-acetyltransferase)|N-acetyltransferase type 2|N-hydroxyarylamine O-acetyltransferase|arylamide acetylase 2	20251125	-
9606	11	NATP	-	AACP|NATP1	HGNC:HGNC:15|AllianceGenome:HGNC:15	8	8p22	N-acetyltransferase pseudogene	pseudo	NATP	N-acetyltransferase pseudogene	O	arylamide acetylase pseudogene	20251125	-
"""
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

#     content = """\
# "uuid"	"gene_curie"	"gene_symbol"	"disease_curie"	"disease_title"	"disease_original_curie"	"disease_original_title"	"classification_curie"	"classification_title"	"moi_curie"	"moi_title"	"submitter_curie"	"submitter_title"	"submitted_as_hgnc_id"	"submitted_as_hgnc_symbol"	"submitted_as_disease_id"	"submitted_as_disease_name"	"submitted_as_moi_id"	"submitted_as_moi_name"	"submitted_as_submitter_id"	"submitted_as_submitter_name"	"submitted_as_classification_id"	"submitted_as_classification_name"	"submitted_as_date"	"submitted_as_public_report_url"	"submitted_as_notes"	"submitted_as_pmids"	"submitted_as_assertion_criteria_url"	"submitted_as_submission_id"	"submitted_run_date"
# "GENCC_000101-HGNC_10896-OMIM_182212-HP_0000006-GENCC_100001"	"HGNC:10896"	"SKI"	"MONDO:0008426"	"Shprintzen-Goldberg syndrome"	"OMIM:182212"	"Shprintzen-Goldberg syndrome"	"GENCC:100001"	"Definitive"	"HP:0000006"	"Autosomal dominant"	"GENCC:000101"	"Ambry Genetics"	"HGNC:10896"	"SKI"	"OMIM:182212"	"Shprintzen-Goldberg syndrome"	"HP:0000006"	"Autosomal dominant inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100001"	"Definitive"	"2018-03-30 13:31:56"	""	""	""	"PMID: 28106320"	"1034"	"2020-12-24"
# "GENCC_000101-HGNC_16636-OMIM_171300-HP_0000006-GENCC_100003"	"HGNC:16636"	"KIF1B"	"MONDO:0008233"	"pheochromocytoma"	"OMIM:171300"	"{Pheochromocytoma, susceptibility to}"	"GENCC:100003"	"Moderate"	"HP:0000006"	"Autosomal dominant"	"GENCC:000101"	"Ambry Genetics"	"HGNC:16636"	"KIF1B"	"OMIM:171300"	"Pheochromocytoma"	"HP:0000006"	"Autosomal dominant inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100003"	"Moderate"	"2019-12-04 13:30:43"	""	""	""	"PMID: 28106320"	"69237"	"2020-12-24"
# "GENCC_000101-HGNC_16636-OMIM_118210-HP_0000006-GENCC_100004"	"HGNC:16636"	"KIF1B"	"MONDO:0007308"	"Charcot-Marie-Tooth disease type 2A1"	"OMIM:118210"	"Charcot-Marie-Tooth disease, type 2A1"	"GENCC:100004"	"Limited"	"HP:0000006"	"Autosomal dominant"	"GENCC:000101"	"Ambry Genetics"	"HGNC:16636"	"KIF1B"	"OMIM:118210"	"Charcot-Marie-Tooth disease, type 2A1"	"HP:0000006"	"Autosomal dominant inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100004"	"Limited"	"2024-10-15 12:08:25"	""	""	""	"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5655771/"	"61327"	"2025-01-17"
# "GENCC_000101-HGNC_17939-OMIM_617532-HP_0000007-GENCC_100004"	"HGNC:17939"	"SLC45A1"	"MONDO:0044322"	"intellectual developmental disorder with neuropsychiatric features"	"OMIM:617532"	"Intellectual developmental disorder with neuropsychiatric features"	"GENCC:100004"	"Limited"	"HP:0000007"	"Autosomal recessive"	"GENCC:000101"	"Ambry Genetics"	"HGNC:17939"	"SLC45A1"	"OMIM:617532"	"Intellectual developmental disorder with neuropsychiatric features"	"HP:0000007"	"Autosomal recessive inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100004"	"Limited"	"2024-09-26 12:08:38"	""	""	""	"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC5655771/"	"17305"	"2025-01-17"
# "GENCC_000101-HGNC_11071-OMIM_616291-HP_0000007-GENCC_100004"	"HGNC:11071"	"SLC9A1"	"MONDO:0014572"	"Lichtenstein-Knorr syndrome"	"OMIM:616291"	"Lichtenstein-Knorr syndrome"	"GENCC:100004"	"Limited"	"HP:0000007"	"Autosomal recessive"	"GENCC:000101"	"Ambry Genetics"	"HGNC:11071"	"SLC9A1"	"OMIM:616291"	"Lichtenstein-Knorr syndrome"	"HP:0000007"	"Autosomal recessive inheritance"	"GENCC:000101"	"Ambry Genetics"	"GENCC:100004"	"Limited"	"2018-08-31 13:32:02"	""	""	""	"PMID: 28106320"	"1705"	"2020-12-24"
# """