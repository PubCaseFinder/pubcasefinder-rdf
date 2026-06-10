package pubcasefinder_260415;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// PanelSearch 원본과 수기 정리 파일을 병합해 NANDO 질환-유전자 연관 RDF를 생성한다.
public class DiseaseGeneNANDO {
	/** PanelSearch와 난병 수기 정리 파일을 병합해 NANDO_Gene_Association.ttl을 생성한다. */
	public static void main(String[] args) throws IOException {

		LinkedHashMap<String, LinkedHashSet<String>> nandoNcbiGeneMap = new LinkedHashMap<String, LinkedHashSet<String>>();

		DiseaseGeneAssociationUtil.MergeStats panelSearchStats =
				DiseaseGeneAssociationUtil.mergeAssociationsFromTsv(
						DiseaseGeneAssociationUtil.NANDO_ASSOCIATION_PATH,
						nandoNcbiGeneMap, 1, 3, "PanelSearch", true);
		System.out.println("NANDO_NCBIGene PanelSearch Count : " + panelSearchStats.added);

		DiseaseGeneAssociationUtil.MergeStats nanbyouStats =
				DiseaseGeneAssociationUtil.mergeAssociationsFromTsv(
						DiseaseGeneAssociationUtil.NANDO_MANUAL_PATH,
						nandoNcbiGeneMap, 4, 7, "Nanbyou", true);
		System.out.println("NANDO_NCBIGene Nanbyou Count : " + nanbyouStats.added);
		System.out.println("NANDO_NCBIGene Overlap : " + nanbyouStats.overlap);

		LinkedHashMap<String, String> sourceUriMap = RdfBuildSupport.createStringMap(
				"PanelSearch", "https://jshg.jp/wp-content/uploads/2024/03/a02edeee573e7797da6a821a5bc48026.pdf",
				"Nanbyou", "https://www.nanbyou.or.jp/");

		DiseaseGeneAssociationUtil.writeGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/NANDO_Gene_Association.ttl",
				nandoNcbiGeneMap,
				"NANDO",
				"nando:",
				"PREFIX nando: <http://nanbyodata.jp/ontology/NANDO_>",
				sourceUriMap);
	}
}
