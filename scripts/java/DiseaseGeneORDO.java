package pubcasefinder_260415;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// Orphanet XML ベースの疾患-遺伝子関連に GenCC を補強して RDF を生成する。
public class DiseaseGeneORDO {
/** Orphanet XML と GenCC を結合し、Orphanet_Gene_Association.ttl を生成する。 */
	public static void main(String[] args) throws Exception {

		LinkedHashMap<String, LinkedHashSet<String>> orphanetNcbiGeneMap =
				DiseaseGeneAssociationUtil.loadOrphanetGeneAssociations(
						DiseaseGeneAssociationUtil.NCBI_GENE_INFO_PATH,
						DiseaseGeneAssociationUtil.ORPHANET_PRODUCT6_PATH);
		System.out.println("Orphanet NCBI Count : " + orphanetNcbiGeneMap.size());

		DiseaseGeneAssociationUtil.GenCCAssociations genccAssociations = DiseaseGeneAssociationUtil.loadGenccDefinitiveAssociations();
		int beforeMerge = orphanetNcbiGeneMap.size();
		DiseaseGeneAssociationUtil.mergeAssociationMaps(orphanetNcbiGeneMap, genccAssociations.orphanetAssociations);
		System.out.println("GenCC_ncbigene_orpha Count : " + (orphanetNcbiGeneMap.size() - beforeMerge));

		LinkedHashMap<String, String> sourceUriMap = RdfBuildSupport.createStringMap(
				"Orphanet", "http://www.orphadata.org/data/xml/en_product6.xml",
				"GenCC", DiseaseGeneAssociationUtil.GENCC_SOURCE_URI);

		DiseaseGeneAssociationUtil.writeGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/Orphanet_Gene_Association.ttl",
				orphanetNcbiGeneMap,
				"ORDO",
				"ordo:Orphanet_",
				"PREFIX ordo: <http://www.orpha.net/ORDO/>",
				sourceUriMap);
	}
}
