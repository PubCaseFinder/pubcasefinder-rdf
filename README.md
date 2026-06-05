# PubCaseFinder-RDF

PubCaseFinder-RDF collects open-source disease, phenotype, and gene resources and
converts them into RDF Turtle files for loading into the PubCaseFinder Virtuoso
database.

## How It Works

The build has two stages.

1. Optional data download

   The Python workflow can download the following resources when the matching
   `*_url` and output `*_path` values are set in `scripts/config.ini`.

   | Config key | Default source |
   | --- | --- |
   | `ncbi_gene_info_url` | https://ftp.ncbi.nlm.nih.gov/gene/DATA/GENE_INFO/Mammalia/Homo_sapiens.gene_info.gz |
   | `omim_mim2gene_data_url` | https://www.omim.org/static/omim/data/mim2gene.txt |
   | `medgen_mim2gene_url` | https://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen |
   | `medgen_omim_hpo_url` | https://ftp.ncbi.nlm.nih.gov/pub/medgen/MedGen_HPO_OMIM_Mapping.txt.gz |
   | `mondo_owl_url` | https://purl.obolibrary.org/obo/mondo/mondo-international.owl |
   | `gencc_submissions_url` | https://thegencc.org/download/action/submissions-export-tsv |
   | `hpo_phenotype_url` | http://purl.obolibrary.org/obo/hp/phenotype.hpoa |
   | `genereviews_omim_url` | https://ftp.ncbi.nlm.nih.gov/pub/GeneReviews/NBKid_shortname_OMIM.txt |

   Data that is not listed above must be downloaded manually and placed at the
   path configured in `scripts/config.ini`.

2. RDF conversion

   `scripts/main.py` runs the RDF build steps in this order.

   | Step | Purpose | Output |
   | --- | --- | --- |
   | `NCBIGeneSummaryHelper` | Generates the NCBI gene summary cache. This only runs when the NCBI `datasets` and `dataformat` tool paths are configured. | `gene_summary.tsv.gz` |
   | `NCBIHGNCGeneCatalog` | Generates the NCBI/HGNC gene catalog. | `all_gene.ttl` |
   | `DiseaseMetadataOMIM` | Generates OMIM disease metadata RDF. | `OMIM.ttl` |
   | `DiseaseMetadataORDO` | Generates Orphanet disease metadata RDF. | `Orphanet.ttl` |
   | `DiseasePhenotypeOMIM` | Generates OMIM disease-phenotype RDF. | `OMIM_HP_Association.ttl` |
   | `DiseasePhenotypeORDO` | Generates Orphanet disease-phenotype RDF. | `Orphanet_HP_Association.ttl` |
   | `DiseaseGeneOMIM` | Generates OMIM disease-gene RDF. | `OMIM_Gene_Association.ttl` |
   | `DiseaseGeneORDO` | Generates Orphanet disease-gene RDF. | `Orphanet_Gene_Association.ttl` |
   | `DiseaseGeneMONDO` | Generates MONDO disease-gene RDF. | `MONDO_Gene_Association.ttl` |
   | `DiseaseGeneNANDO` | Generates NANDO disease-gene RDF. | `NANDO_Gene_Association.ttl` |
   | `DiseaseGeneGenCC` | Generates GenCC disease-gene RDF. | `GenCC_Gene_Association.ttl` |
   | `HP_ja` | Generates Japanese HPO label RDF. | `HPO_ja.ttl` |

## Input Data

The Docker workflow expects source files under `data/source` by default. The
default config values point to a dated or `latest` layout such as
`data/source/NCBIGene/latest/Homo_sapiens.gene_info.gz`. If your files are in a
different layout, set the corresponding `*_path` value in `scripts/config.ini`.

Common manually managed resources include:

| Data | Source |
| --- | --- |
| `en_product4.xml` | Orphadata phenotypes associated with rare disorders: http://www.orphadata.org/data/xml/en_product4.xml |
| `en_product6.xml` | Orphadata genes associated with rare diseases: http://www.orphadata.org/data/xml/en_product6.xml |
| `nando_gene_association.txt` | PanelSearch disease-gene association data |
| `shitei_gene_all_250819.txt` | PanelSearch manual disease-gene data |
| `HPO-japanese.alpha.21Jul2023.tsv` | HPO Japanese labels: https://github.com/ogishima/HPO-Japanese |
| `HPO_Inheritance_en_jp.txt` | HPO inheritance Japanese mapping |
| `KEGG_disease.tsv` | KEGG disease data: https://www.kegg.jp/kegg/download/ |

The legacy Java archive also used files such as `HGNC_custom.txt`,
`OMIM_id_ja.txt`, `HPO_id_ja.txt`, `UR_DBMS_DiseaseLinkOMIM.csv`, and
`UR_DBMS_DiseaseLink.csv`. Those files are still kept in `data/source` for
reference and reproducibility of older workflows.

### HGNC Custom File Notes

The archived Java workflow used `HGNC_custom.txt`. To recreate it from
https://www.genenames.org/download/custom/:

1. Unselect all fields.
2. Select `HGNC ID` and `Approved symbol` under "Curated by the HGNC".
3. Select `NCBI Gene ID(supplied by NCBI)` under "Downloaded from external sources".
4. Select only the `Approved` status.
5. Submit and download the generated file.

The file should contain columns like:

```text
HGNC ID    Approved symbol    NCBI Gene ID(supplied by NCBI)
HGNC:5     A1BG               1
HGNC:37133 A1BG-AS1           503538
HGNC:24086 A1CF               29974
```

## Usage

1. Clone the repository.

   ```bash
   git clone https://github.com/PubCaseFinder/pubcasefinder-rdf.git
   cd pubcasefinder-rdf
   ```

2. Build the container image.

   ```bash
   docker compose build
   ```

3. Create and edit `scripts/config.ini`.

   ```bash
   cp scripts/config.ini.template scripts/config.ini
   vi scripts/config.ini
   ```

   If you already have the source files locally, leave the matching `*_url`
   values empty and set the `*_path` values as needed. If you want the workflow
   to download a supported resource, set both its `*_url` and output `*_path`.

   The main configurable values are:

   ```ini
   ncbi_gene_info_path=
   ncbi_gene_summary_path=
   ncbi_gene_datasets_path=
   ncbi_gene_dataformat_path=
   ncbi_gene_info_url=
   omim_mim2gene_data_path=
   omim_mim2gene_data_url=
   medgen_mim2gene_path=
   medgen_mim2gene_url=
   medgen_omim_hpo_path=
   medgen_omim_hpo_url=
   orphanet_product4_path=
   orphanet_product6_path=
   mondo_owl_path=
   mondo_owl_url=
   gencc_submissions_path=
   gencc_submissions_url=
   panelsearch_association_path=
   panelsearch_manual_path=
   hpo_phenotype_path=
   hpo_phenotype_url=
   hpo_inheritance_ja_path=
   hpo_japanese_path=
   kegg_disease_path=
   genereviews_omim_path=
   genereviews_omim_url=
   rdf_output_dir=
   ```

4. Create and edit `.env`.

   ```bash
   cp template.env .env
   vi .env
   ```

   `DATA_SOURCE_DIRECTORY` is mounted as `/data/source` in the container, and
   `RDF_DATA_DIRECTORY` is mounted as `/data/rdf`.

5. Run the full RDF build.

   ```bash
   docker compose run --rm rdf_create_tools uv run python3 main.py
   ```

   The full build usually takes about 20 minutes. New Turtle files are written
   to the directory configured by `rdf_output_dir`; with the default Docker
   layout, this is the host directory configured by `RDF_DATA_DIRECTORY`.

## Running Individual Steps

Data download and RDF conversion modules can also be run individually.

```bash
# docker compose run --rm rdf_create_tools uv run python3 -m package.<module_name>
docker compose run --rm rdf_create_tools uv run python3 -m package.disease_gene_nando
```

Useful module names include:

```text
package.get_data_helper
package.ncbi_hgnc_gene_catalog
package.disease_metadata_omim
package.disease_metadata_ordo
package.disease_phenotype_omim
package.disease_phenotype_ordo
package.disease_gene_omim
package.disease_gene_ordo
package.disease_gene_mondo
package.disease_gene_nando
package.disease_gene_gencc
package.hp_ja
```

## Legacy Java Sources

The current workflow is the Docker and Python workflow described above. Older
Java implementations are retained under `scripts/archives` and `scripts/java`
for reference. Those sources require a JDK, not only a JRE, because they must be
compiled before running.

## Contact

- Jae-Moon Shin (shin@dbcls.rois.ac.jp)
