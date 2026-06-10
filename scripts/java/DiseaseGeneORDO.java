package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// Orphanet XML 기반 질환-유전자 연관에 GenCC를 보강해 RDF를 생성한다.
public class DiseaseGeneORDO {
	/** Orphanet XML과 GenCC를 병합해 Orphanet_Gene_Association.ttl을 생성한다. */
	public static void main(String[] args) throws Exception {

		LinkedHashMap<String, LinkedHashSet<String>> orphanetNcbiGeneMap =
				DiseaseGeneAssociationUtil.loadOrphanetGeneAssociations(
						DiseaseGeneAssociationUtil.NCBI_GENE_INFO_PATH,
						DiseaseGeneAssociationUtil.ORPHANET_PRODUCT6_PATH);
		System.out.println("Orphanet NCBI Count : " + orphanetNcbiGeneMap.size());

		DiseaseGeneAssociationUtil.GenCCAssociations genccAssociations = DiseaseGeneAssociationUtil.loadGenccDefinitiveAssociations();
		int beforeMerge = orphanetNcbiGeneMap.size();
		DiseaseGeneAssociationUtil.mergeAssociationMaps(orphanetNcbiGeneMap, genccAssociations.orphanetAssociations);
		System.out.println("GenCC_ncbigene_orpha Count : " + (orphanetNcbiGeneMap.size() - beforeMerge));

		LinkedHashMap<String, String> sourceUriMap = RdfBuildSupport.createStringMap(
				"Orphanet", "http://www.orphadata.org/data/xml/en_product6.xml",
				"GenCC", DiseaseGeneAssociationUtil.GENCC_SOURCE_URI);

		DiseaseGeneAssociationUtil.writeGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/Orphanet_Gene_Association.ttl",
				orphanetNcbiGeneMap,
				"ORDO",
				"ordo:Orphanet_",
				"PREFIX ordo: <http://www.orpha.net/ORDO/>",
				sourceUriMap);
	}
}
