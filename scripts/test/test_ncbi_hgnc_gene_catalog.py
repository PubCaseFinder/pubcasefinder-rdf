import duckdb
from rdflib import Graph, Literal, Namespace
from rdflib.namespace import DCTERMS, RDF, RDFS

from package import ncbi_hgnc_gene_catalog


def test_parse_dbxrefs():
    assert ncbi_hgnc_gene_catalog.parse_dbxrefs(None) is None
    assert ncbi_hgnc_gene_catalog.parse_dbxrefs("-") is None
    assert ncbi_hgnc_gene_catalog.parse_dbxrefs(
        "MIM:138670|HGNC:HGNC:5|Ensembl:ENSG00000121410"
    ) == {
        "hgnc_id": "5",
        "mim_id": "138670",
    }
    assert ncbi_hgnc_gene_catalog.parse_dbxrefs("HGNC:HGNC:7") == {
        "hgnc_id": "7",
        "mim_id": "",
    }
    assert ncbi_hgnc_gene_catalog.parse_dbxrefs("HGNC:HGNC:15|MIM:108345") == {
        "hgnc_id": "15",
        "mim_id": "108345",
    }


def test_ncbi_hgnc_gene_catalog(tmp_path, mocker):
    human_gene_path = tmp_path / "Homo_sapiens.gene_info"
    human_gene_path.write_text(
        "GeneID,Symbol,Synonyms,dbXrefs,map_location,description,type_of_gene,Other_designations\n"
        "1,A1BG,A1B|ABG,MIM:138670|HGNC:HGNC:5,19q13.43,alpha-1-B glycoprotein,protein-coding,alpha-1B-glycoprotein\n"
        "2,A2M,-,-,-,alpha-2-macroglobulin,protein-coding,-\n",
        encoding="utf-8",
    )
    gene_summary_path = tmp_path / "gene_summary.tsv"
    gene_summary_path.write_text(
        '"NCBI GeneID","Summary Description"\n'
        "1,A1BG summary\n",
        encoding="utf-8",
    )
    output_path = tmp_path / "all_gene.ttl"

    duckdb_connect = duckdb.connect
    mocker.patch.object(
        ncbi_hgnc_gene_catalog.duckdb,
        "connect",
        lambda _path: duckdb_connect(":memory:"),
    )

    ncbi_hgnc_gene_catalog.ncbi_hgnc_gene_catalog(
        human_gene_path,
        gene_summary_path,
        output_path,
    )

    graph = Graph()
    graph.parse(output_path, format="turtle")

    HGNC = Namespace("https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:")
    NCBIGENE = Namespace("http://identifiers.org/ncbigene/")
    NCIT = Namespace("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#")
    MED2RDF = Namespace("http://med2rdf.org/ontology/")
    MIM = Namespace("https://omim.org/entry/")
    OBO = Namespace("http://purl.obolibrary.org/obo/")
    SIO = Namespace("http://semanticscience.org/resource/")
    NUC = Namespace("http://ddbj.nig.ac.jp/ontologies/nucleotide/")
    HOP = Namespace("http://purl.org/net/orthordf/hOP/ontology#")

    gene = NCBIGENE["1"]
    hgnc = HGNC["5"]

    assert (gene, RDF.type, MED2RDF.Gene) in graph
    assert (gene, RDF.type, NCIT["C16612"]) in graph
    assert (gene, DCTERMS.identifier, Literal("1")) in graph
    assert (gene, RDFS.label, Literal("A1BG")) in graph
    assert (gene, DCTERMS.description, Literal("alpha-1-B glycoprotein")) in graph
    assert (gene, HOP.typeOfGene, Literal("protein-coding")) in graph
    assert (gene, NUC.gene_synonym, Literal("A1B")) in graph
    assert (gene, NUC.gene_synonym, Literal("ABG")) in graph
    assert (gene, NUC.map, Literal("19q13.43")) in graph
    assert (gene, DCTERMS.alternative, Literal("alpha-1B-glycoprotein")) in graph
    assert (gene, SIO["SIO_000205"], hgnc) in graph
    assert (gene, RDFS.seeAlso, MIM["138670"]) in graph
    assert (gene, OBO["NCIT_C42581"], Literal("A1BG summary")) in graph
    assert (hgnc, RDF.type, NCIT["C43568"]) in graph
    assert (hgnc, RDFS.label, Literal("A1BG")) in graph
