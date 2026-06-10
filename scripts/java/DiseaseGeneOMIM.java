package pubcasefinder_260415;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// MedGen 기반 OMIM 질환-유전자 연관에 GenCC를 보강해 RDF를 생성한다.
public class DiseaseGeneOMIM {
	/** MedGen과 GenCC를 병합해 OMIM_Gene_Association.ttl을 생성한다. */
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
