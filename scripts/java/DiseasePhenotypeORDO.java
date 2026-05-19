package pubcasefinder_260415;

import java.util.LinkedHashMap;

// Orphanet-HPO 表現型関連と頻度注釈を結合し、Orphanet_HP_Association.ttl を生成する。
public class DiseasePhenotypeORDO {
/** Orphanet の頻度情報と手動 HPO 関連を結合し、Orphanet_HP_Association.ttl を生成する。 */
	public static void main(String[] args) throws Exception {
		LinkedHashMap<String, String> orphanetFrequency =
				DiseasePhenotypeAssociationUtil.loadOrdoFrequencyAnnotations(
						DiseasePhenotypeAssociationUtil.ORPHANET_PRODUCT4_PATH);
		System.out.println("Orphanet_frequency Count : " + orphanetFrequency.size());

		LinkedHashMap<String, String> orphanetManual =
				DiseasePhenotypeAssociationUtil.loadManualPhenotypeAssociations(
						DiseasePhenotypeAssociationUtil.HPO_PHENOTYPE_PATH,
						"ORPHA");
		System.out.println("Orphanet_HPO_Manual Count : " + orphanetManual.size());

		DiseasePhenotypeAssociationUtil.AnnotationSource source =
				DiseasePhenotypeAssociationUtil.createAnnotationSource(
						"Orphanet",
						DiseasePhenotypeAssociationUtil.HPOA_SOURCE_URI);

		DiseasePhenotypeAssociationUtil.writeOrdoPhenotypeAssociationTtl(
				DiseasePhenotypeAssociationUtil.RDF_DIR + "/Orphanet_HP_Association.ttl",
				orphanetManual,
				orphanetFrequency,
				source);
		System.out.println("Orphanet_HPO_Association Count : " + orphanetManual.size());
	}
}
