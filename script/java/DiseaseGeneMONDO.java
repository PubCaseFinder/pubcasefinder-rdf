package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// 元の疾患マッピングを MONDO に拡張し、MONDO 疾患-遺伝子関連 RDF を生成する。
public class DiseaseGeneMONDO {
/** 拡張後の MONDO 疾患-遺伝子関連を計算し、MONDO_Gene_Association.ttl を生成する。 */
	public static void main(String[] args) throws Exception {
		LinkedHashMap<String, LinkedHashSet<String>> mondoNcbiGeneMap =
				DiseaseGeneAssociationUtil.buildMondoGeneAssociations();
		System.out.println("MONDO_Gene_Association Count : " + mondoNcbiGeneMap.size());

		LinkedHashMap<String, String> sourceUriMap = RdfBuildSupport.createStringMap(
				"MedGen", "ftp://ftp.ncbi.nlm.nih.gov/gene/DATA/mim2gene_medgen",
				"Orphanet", "http://www.orphadata.org/data/xml/en_product6.xml",
				"GenCC", DiseaseGeneAssociationUtil.GENCC_SOURCE_URI);

		DiseaseGeneAssociationUtil.writeGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/MONDO_Gene_Association.ttl",
				mondoNcbiGeneMap,
				"MONDO",
				"obo:MONDO_",
				"PREFIX obo: <http://purl.obolibrary.org/obo/>",
				sourceUriMap);
	}
}
