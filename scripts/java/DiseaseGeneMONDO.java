package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// 원본 질환 매핑을 MONDO로 확장해 MONDO 질환-유전자 연관 RDF를 생성한다.
public class DiseaseGeneMONDO {
	/** 확장된 MONDO 질환-유전자 연관을 계산해 MONDO_Gene_Association.ttl을 생성한다. */
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
