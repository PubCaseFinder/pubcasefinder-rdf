package pubcasefinder_260415;

import java.util.LinkedHashMap;

// 수동 OMIM-HPO 표현형 연관을 RDF로 변환해 OMIM_HP_Association.ttl을 생성한다.
public class DiseasePhenotypeOMIM {
	/** HPOA 기반 수동 OMIM 표현형 연관을 읽어 OMIM_HP_Association.ttl을 생성한다. */
	public static void main(String[] args) throws Exception {
		LinkedHashMap<String, String> omimManual =
				DiseasePhenotypeAssociationUtil.loadManualPhenotypeAssociations(
						DiseasePhenotypeAssociationUtil.HPO_PHENOTYPE_PATH,
						"OMIM");
		System.out.println("OMIM_HPO_Manual Count : " + omimManual.size());

		DiseasePhenotypeAssociationUtil.AnnotationSource source =
				DiseasePhenotypeAssociationUtil.createAnnotationSource(
						"Human Phenotype Ontology Consortium",
						DiseasePhenotypeAssociationUtil.HPOA_SOURCE_URI);

		DiseasePhenotypeAssociationUtil.writeManualPhenotypeAssociationTtl(
				DiseasePhenotypeAssociationUtil.RDF_DIR + "/OMIM_HP_Association.ttl",
				"OMIM",
				"mim:",
				"PREFIX mim: <https://omim.org/entry/>",
				omimManual,
				source);
		System.out.println("OMIM manual Count : " + omimManual.size());
	}
}
