from dataclasses import dataclass

import duckdb
from rdflib import Graph, Namespace, Literal
from rdflib.namespace import DCTERMS, RDF, RDFS

from utils.log_util import get_logger

logger = get_logger()

@dataclass
class NCBIHGNCGeneCatalogConfig(object):
    gene_summary_path: str
    human_gene_path: str
    ncbi_hgnc_gene_catalog_path: str


def parse_dbxrefs(xrefs: str) -> dict[str, str]:
    if xrefs is None or xrefs == '-':
        return
    xref_set = {
        'hgnc_id': '',
        'mim_id': ''
    }
    for ref in xrefs.split('|'):
        if ref.startswith('HGNC:HGNC:'):
            xref_set["hgnc_id"] = ref[len('HGNC:HGNC:'):]
        elif ref.startswith('HGNC:HGNC:'):
            xref_set["hgnc_id"] = ref[len('HGNC:'):]
        elif ref.startswith('MIM:'):
            xref_set["hgnc_id"] = ref[len('MIM:'):]
    return xref_set



def ncbi_hgnc_gene_catalog(config: NCBIHGNCGeneCatalogConfig):
    # https://duckdb.org/docs/current/configuration/pragmas#memory-limit
    duckdb.execute('set memory_limit = "2GB"')

    con = duckdb.connect('tmp.duckdb')
    qery_statement = f'''
        select
            GeneID,
            Symbol,
            Synonyms,
            dbXrefs,
            map_location,
            description,
            type_of_gene,
            Other_designations,
            "Summary Description"
        from read_csv("{config.human_gene_path}") as gene_info
        left join read_csv("{config.gene_summary_path}") as gene_summary
        on gene_info.GeneID = gene_summary."NCBI GeneID"
    '''
    con.execute(qery_statement)

    g = Graph()
    HGNC = Namespace("https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:")
    NCBIGENE = Namespace("http://identifiers.org/ncbigene/")
    NCIT = Namespace("http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#")
    MED2RDF = Namespace("http://med2rdf.org/ontology/")
    MIM = Namespace("https://omim.org/entry/")
    OBO = Namespace("http://purl.obolibrary.org/obo/")
    SIO = Namespace("http://semanticscience.org/resource/")
    NUC = Namespace("http://ddbj.nig.ac.jp/ontologies/nucleotide/")
    HOP = Namespace("http://purl.org/net/orthordf/hOP/ontology#")
    g.bind("dcterms", DCTERMS)
    g.bind("hgnc", HGNC)
    g.bind("ncbigene", NCBIGENE)
    g.bind("ncit", NCIT)
    g.bind("med2rdf", MED2RDF)
    g.bind("mim", MIM)
    g.bind("obo", OBO)
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("sio", SIO)
    g.bind("nuc", NUC)
    g.bind("hop", HOP)


    while True:

        row = con.fetchone()
        if row is None:
            break

        gene_id = row[0]
        symbol = row[1]
        synonyms = row[2]
        dbxrefs = row[3]
        map_location = row[4]
        description = row[5]
        type_of_gene = row[6]
        other_designations = row[7]
        summary_description = row[8]

        hgnc_id = ''
        mim_id = ''

        xref_set = parse_dbxrefs(dbxrefs)

        if xref_set is not None:
            hgnc_id = xref_set['hgnc_id']
            mim_id = xref_set['mim_id']

        gene = NCBIGENE[str(gene_id)]

        if synonyms != None:
            # list_synonyms = ', '.join([ f'"{i}"' for i in synonyms.split('|')])
            for s in synonyms.split('|'):
                g.add((gene, NUC.gene_synonym, Literal(s)))
        if map_location != '-':
            g.add((gene, NUC.map, Literal(map_location)))
        if other_designations != '-':
            g.add((gene, DCTERMS.alternative, Literal(other_designations)))
        if hgnc_id != '':
            hgnc = 'hgnc:' + hgnc_id
            g.add((gene, SIO['SIO_000205'], Literal(hgnc)))
        if mim_id != '':
            mim = 'mim:' + mim_id
            g.add((gene, RDFS.seeAlso, Literal(mim)))
        if summary_description is not None and summary_description != '-':
            g.add((gene, OBO['NCIT_C42581'], Literal(summary_description)))

        g.add((gene, DCTERMS.identifier, Literal(gene_id)))
        g.add((gene, RDFS.label, Literal(symbol)))
        g.add((gene, DCTERMS.description, Literal(description)))
        g.add((gene, HOP.typeOfGene, Literal(type_of_gene)))
        g.add((gene, RDF.type, MED2RDF.Gene))
        g.add((gene, RDF.type, NCIT["C16612"]))

        if hgnc_id != '':
            hgnc = HGNC[str(hgnc_id)]
            g.add((hgnc, RDF.type, NCIT['C43568']))
            g.add((hgnc, RDFS.label, Literal(symbol)))

    g.serialize(destination=config.ncbi_hgnc_gene_catalog_path, format="turtle", encoding="utf-8")


tmp = NCBIHGNCGeneCatalogConfig(
    '../data/NCBIGene/latest/gene_summary.tsv',
    '../data/NCBIGene/latest/Homo_sapiens.gene_info',
    '../data/NCBIGene/latest/all_gene_1.ttl'
)
ncbi_hgnc_gene_catalog(tmp)
