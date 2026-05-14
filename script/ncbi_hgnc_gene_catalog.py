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


def parse_dbxrefs(xrefs: str) -> dict[str, str] | None:
    if xrefs is None or xrefs == '-':
        return None
    xref_set = {
        'hgnc_id': '',
        'mim_id': ''
    }
    for ref in xrefs.split('|'):
        if ref.startswith('HGNC:HGNC:'):
            xref_set["hgnc_id"] = ref[len('HGNC:HGNC:'):]
        elif ref.startswith('HGNC:'):
            xref_set["hgnc_id"] = ref[len('HGNC:'):].replace('HGNC:', '')
        elif ref.startswith('MIM:'):
            xref_set["mim_id"] = ref[len('MIM:'):]
    return xref_set



def ncbi_hgnc_gene_catalog(config: NCBIHGNCGeneCatalogConfig):
    logger.info(
        'start NCBI/HGNC gene catalog RDF build: human_gene=%s summary=%s output=%s',
        config.human_gene_path,
        config.gene_summary_path,
        config.ncbi_hgnc_gene_catalog_path
    )

    # https://duckdb.org/docs/current/configuration/pragmas#memory-limit
    duckdb.execute('set memory_limit = "2GB"')

    con = duckdb.connect('tmp.duckdb')
    query_statement = f'''
        select
            gene_info.GeneID,
            gene_info.Symbol,
            nullif(gene_info.Synonyms, '-') as Synonyms,
            nullif(gene_info.dbXrefs, '-') as dbXrefs,
            nullif(gene_info.map_location, '-') as map_location,
            description,
            type_of_gene,
            nullif(gene_info.Other_designations, '-') as Other_designations,
            nullif(gene_summary."Summary Description", '-') as "Summary Description"
        from read_csv("{config.human_gene_path}") as gene_info
        left join read_csv("{config.gene_summary_path}") as gene_summary
        on gene_info.GeneID = gene_summary."NCBI GeneID"
    '''
    logger.info('executing DuckDB query')
    con.execute(query_statement)
    logger.info('DuckDB query started; building RDF graph')

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

    processed_count = 0
    synonym_count = 0
    hgnc_count = 0
    mim_count = 0
    summary_count = 0


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

        # TODO: [debug用]
        # print(gene_id, symbol, synonyms, map_location)
        # print('---------------------------')


        gene = NCBIGENE[str(gene_id)]

        if synonyms is not None:
            # list_synonyms = ', '.join([ f'"{i}"' for i in synonyms.split('|')])
            for s in synonyms.split('|'):
                g.add((gene, NUC.gene_synonym, Literal(s)))
                synonym_count += 1
        if map_location is not None:
            g.add((gene, NUC.map, Literal(map_location)))
        if other_designations is not None:
            g.add((gene, DCTERMS.alternative, Literal(other_designations)))
        if hgnc_id != '':
            hgnc = HGNC[str(hgnc_id)]
            g.add((gene, SIO['SIO_000205'], hgnc))
            hgnc_count += 1
        if mim_id != '':
            mim = MIM[str(mim_id)]
            g.add((gene, RDFS.seeAlso, mim))
            mim_count += 1
        if summary_description is not None:
            g.add((gene, OBO['NCIT_C42581'], Literal(summary_description)))
            summary_count += 1

        g.add((gene, DCTERMS.identifier, Literal(str(gene_id))))
        g.add((gene, RDFS.label, Literal(symbol)))
        g.add((gene, DCTERMS.description, Literal(description)))
        g.add((gene, HOP.typeOfGene, Literal(type_of_gene)))
        g.add((gene, RDF.type, MED2RDF.Gene))
        g.add((gene, RDF.type, NCIT["C16612"]))

        if hgnc_id != '':
            hgnc = HGNC[str(hgnc_id)]
            g.add((hgnc, RDF.type, NCIT['C43568']))
            g.add((hgnc, RDFS.label, Literal(symbol)))

        processed_count += 1
        if processed_count % 10000 == 0:
            logger.info('processed %s genes; current_triples=%s', processed_count, len(g))

    logger.info(
        'built RDF graph: genes=%s triples=%s synonyms=%s hgnc_links=%s mim_links=%s summaries=%s',
        processed_count,
        len(g),
        synonym_count,
        hgnc_count,
        mim_count,
        summary_count
    )
    logger.info('serializing RDF graph: output=%s', config.ncbi_hgnc_gene_catalog_path)
    g.serialize(destination=config.ncbi_hgnc_gene_catalog_path, format="turtle", encoding="utf-8")
    logger.info('finished serializing RDF graph: output=%s triples=%s', config.ncbi_hgnc_gene_catalog_path, len(g))


## TODO: 最終的には削除
tmp = NCBIHGNCGeneCatalogConfig(
    '../data/NCBIGene/latest/gene_summary_1.tsv.gz',
    '../data/NCBIGene/latest/Homo_sapiens.gene_info',
    '../data/NCBIGene/latest/all_gene_1.ttl'
)
ncbi_hgnc_gene_catalog(tmp)
