package pubcasefinder_260415;

import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;

// PanelSearch の元データと手作業で整理したファイルを結合し、NANDO 疾患-遺伝子関連 RDF を生成する。
public class DiseaseGeneNANDO {
/** PanelSearch と難病の手作業整理ファイルを結合し、NANDO_Gene_Association.ttl を生成する。 */
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
