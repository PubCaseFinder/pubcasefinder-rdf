package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// Orphanet 疾患メタデータを組み合わせて Orphanet.ttl を生成する。
public class DiseaseMetadataORDO {
/** 共有マッピングと外部参照を用いて Orphanet.ttl を生成する。 */
	public static void main(String[] args) throws Exception {
// OMIM と Orphanet のメタデータで同じ基準を使えるよう、共通マッピング資源を再利用する。
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
