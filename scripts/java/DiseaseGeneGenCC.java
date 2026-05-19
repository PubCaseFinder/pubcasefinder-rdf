package pubcasefinder_260415;

import java.io.IOException;
import java.util.ArrayList;

// GenCC の元 submission を独立した疾患-遺伝子関連 TTL として出力する。
public class DiseaseGeneGenCC {
/** GenCC submission の元データを読み込み、GenCC_Gene_Association.ttl を生成する。 */
	public static void main(String[] args) throws IOException {
		// <ファイル名.そのファイルで定義された型>
		// DiseaseGeneAssociationUtil.java ↓
		// public static class GenCCSubmissionRecord {
		// 	String genccId;
		// 	String ncbiGeneId;
		// 	String diseaseCurie;
		// 	String classificationTitle;
		// 	String moiCurie;
		// 	String submitterLabel;
		// }
		//
		// public static ArrayList<GenCCSubmissionRecord> loadGenccSubmissionRecords() throws IOException {
		// 	pcf-rdf.propertiesにあるパスを読み取って
		// 	return loadGenccSubmissionRecords(GENCC_SUBMISSIONS_PATH, NCBI_GENE_INFO_PATH);
		// }
		//
		// public static final String GENCC_SUBMISSIONS_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "gencc.submissions.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "gencc.dir"), "gencc-submissions.tsv");
		// public static final String NCBI_GENE_INFO_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "ncbigene.file.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "ncbigene.dir"), "Homo_sapiens.gene_info.gz");



		ArrayList<DiseaseGeneAssociationUtil.GenCCSubmissionRecord> records =
				DiseaseGeneAssociationUtil.loadGenccSubmissionRecords();
		System.out.println("GenCC submission count : " + records.size());

		DiseaseGeneAssociationUtil.writeGenccGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/GenCC_Gene_Association.ttl",
				records);
	}
}
