package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// OMIM 질환 메타데이터를 조합해 OMIM.ttl을 생성한다.
public class DiseaseMetadataOMIM {
	/** OMIM ID 집합과 외부 매핑 정보를 결합해 OMIM.ttl을 생성한다. */
	public static void main(String[] args) throws Exception {
		// 명시적인 OMIM 질환 ID 집합을 시작점으로 삼고, 외부 매핑과 참조 정보를 덧붙인다.
		LinkedHashSet<String> omimIds = DiseaseMetadataUtil.loadOmimDiseaseIds(DiseaseMetadataUtil.OMIM_MIM2GENE_PATH);
		System.out.println("OMIM All Count : " + omimIds.size());

		DiseaseMetadataUtil.SharedReferenceData referenceData =
				DiseaseMetadataUtil.loadSharedReferenceData();
		System.out.println("OMIM inheritance Count : " + referenceData.inheritanceMap.size());
		omimIds.addAll(referenceData.mappings.omimToMondo.keySet());
		System.out.println("OMIM KEGG Count : " + referenceData.keggMap.size());
		System.out.println("OMIM Gene_Review Count : " + referenceData.geneReviewsMap.size());

		DiseaseMetadataUtil.writeOmimDiseaseTtl(
				DiseaseMetadataUtil.RDF_DIR + "/OMIM.ttl",
				omimIds,
				referenceData.inheritanceMap,
				referenceData.mappings,
				referenceData.keggMap,
				referenceData.geneReviewsMap);
		System.out.println("OMIM All Count : " + omimIds.size());
	}
}
