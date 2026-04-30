package pubcasefinder_260415;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// MedGen ベースの OMIM 疾患-遺伝子関連に GenCC を補強して RDF を生成する。
public class DiseaseGeneOMIM {
/** MedGen と GenCC を結合し、OMIM_Gene_Association.ttl を生成する。 */
	public static void main(String[] args) throws IOException {

		LinkedHashMap<String, LinkedHashSet<String>> omimNcbiGeneMap =
				DiseaseGeneAssociationUtil.loadOmimGeneAssociations(DiseaseGeneAssociationUtil.MEDGEN_MIM2GENE_PATH);
		System.out.println("OMIM_NCBIGene All Count : " + omimNcbiGeneMap.size());

		try {
			DiseaseGeneAssociationUtil.GenCCAssociations genccAssociations = DiseaseGeneAssociationUtil.loadGenccDefinitiveAssociations();
			int beforeMerge = omimNcbiGeneMap.size();
			DiseaseGeneAssociationUtil.mergeAssociationMaps(omimNcbiGeneMap, genccAssociations.omimAssociations);
			System.out.println("GenCC_ncbigene_omim Count : " + (omimNcbiGeneMap.size() - beforeMerge));
		}
		catch (Exception e) {
			throw new IOException("Failed to load GenCC associations", e);
		}

		LinkedHashMap<String, String> sourceUriMap = RdfBuildSupport.createStringMap(
				"MedGen", "ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen",
				"GenCC", DiseaseGeneAssociationUtil.GENCC_SOURCE_URI);

		DiseaseGeneAssociationUtil.writeGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/OMIM_Gene_Association.ttl",
				omimNcbiGeneMap,
				"OMIM",
				"mim:",
				"PREFIX mim: <https://omim.org/entry/>",
				sourceUriMap);
	}
}
