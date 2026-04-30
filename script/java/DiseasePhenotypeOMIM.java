package pubcasefinder_260415;

import java.util.LinkedHashMap;

// 手動管理の OMIM-HPO 表現型関連を RDF に変換し、OMIM_HP_Association.ttl を生成する。
public class DiseasePhenotypeOMIM {
/** HPOA ベースの手動 OMIM 表現型関連を読み込み、OMIM_HP_Association.ttl を生成する。 */
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
