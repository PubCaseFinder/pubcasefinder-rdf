package pubcasefinder_260415;

import java.util.LinkedHashMap;

// Orphanet-HPO 표현형 연관과 빈도 주석을 결합해 Orphanet_HP_Association.ttl을 생성한다.
public class DiseasePhenotypeORDO {
	/** Orphanet 빈도 정보와 수동 HPO 연관을 합쳐 Orphanet_HP_Association.ttl을 생성한다. */
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
