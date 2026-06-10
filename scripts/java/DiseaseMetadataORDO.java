package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// Orphanet 질환 메타데이터를 조합해 Orphanet.ttl을 생성한다.
public class DiseaseMetadataORDO {
	/** 공유 매핑과 외부 참조를 이용해 Orphanet.ttl을 생성한다. */
	public static void main(String[] args) throws Exception {
		// OMIM과 Orphanet 메타데이터가 같은 기준을 쓰도록 공통 매핑 리소스를 재사용한다.
		DiseaseMetadataUtil.SharedReferenceData referenceData =
				DiseaseMetadataUtil.loadSharedReferenceData();
		System.out.println("OMIM inheritance Count : " + referenceData.inheritanceMap.size());
		System.out.println("Orphanet Count : " + referenceData.mappings.orphanetIds.size());
		System.out.println("OMIM KEGG Count : " + referenceData.keggMap.size());
		System.out.println("OMIM Gene_Review Count : " + referenceData.geneReviewsMap.size());

		DiseaseMetadataUtil.writeOrphanetDiseaseTtl(
				DiseaseMetadataUtil.RDF_DIR + "/Orphanet.ttl",
				referenceData.mappings,
				referenceData.inheritanceMap,
				referenceData.keggMap,
				referenceData.geneReviewsMap);
		System.out.println("Orphanet All Count : " + referenceData.mappings.orphanetIds.size());
	}
}
