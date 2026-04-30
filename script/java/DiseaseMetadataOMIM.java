package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// OMIM 疾患メタデータを組み合わせて OMIM.ttl を生成する。
public class DiseaseMetadataOMIM {
/** OMIM ID 集合と外部マッピング情報を結合し、OMIM.ttl を生成する。 */
	public static void main(String[] args) throws Exception {
// 明示的な OMIM 疾患 ID 集合を出発点とし、外部マッピングと参照情報を付加する。
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
