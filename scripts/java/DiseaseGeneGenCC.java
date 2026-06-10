package pubcasefinder_260415;

import java.io.IOException;
import java.util.ArrayList;

// GenCC 원본 submission을 독립적인 질환-유전자 연관 TTL로 출력한다.
public class DiseaseGeneGenCC {
	/** GenCC submission 원본을 읽어 GenCC_Gene_Association.ttl을 생성한다. */
	public static void main(String[] args) throws IOException {
		ArrayList<DiseaseGeneAssociationUtil.GenCCSubmissionRecord> records =
				DiseaseGeneAssociationUtil.loadGenccSubmissionRecords();
		System.out.println("GenCC submission count : " + records.size());

		DiseaseGeneAssociationUtil.writeGenccGeneAssociationTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/GenCC_Gene_Association.ttl",
				records);
	}
}
