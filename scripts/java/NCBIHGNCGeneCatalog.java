package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Properties;

class GeneInfoRecord {
	String geneId;
	String symbol;
	LinkedHashSet<String> synonyms = new LinkedHashSet<String>();
	String hgncId;
	String mimId;
	String mapLocation;
	String description;
	String typeOfGene;
	String otherDesignations;
	String summary;
}

// NCBI gene_info、HGNC 連携情報、gene summary を結合して all_gene.ttl を生成するユーティリティ
public class NCBIHGNCGeneCatalog {
	private static final Properties CONFIG = RdfBuildSupport.loadConfig();
	// RDF/latest/all_gene.ttl
	private static final String OUTPUT_PATH = DiseaseGeneAssociationUtil.RDF_DIR + "/all_gene.ttl";
	private static final String SUMMARY_PATH_KEY = "ncbigene.summary.path";
	private static final String NCBI_GENE_DIR_KEY = "ncbigene.dir";
	private static final String DATASETS_PATH_KEY = "ncbigene.datasets.path";
	private static final String DATAFORMAT_PATH_KEY = "ncbigene.dataformat.path";

	/** gene summary と gene_info を結合し、all_gene.ttl を生成する。 */
	// 🤔
	public static void main(String[] args) throws Exception {
		LinkedHashMap<String, String> geneSummaryMap = loadGeneSummaryMap();
		System.out.println("NCBI gene summary Count : " + geneSummaryMap.size());

		// ncbigene.file.pathからとってきたデータに対して、summaryをくっつける
		// ncbigene.file.path = data/NCBIGene/latest/Homo_sapiens.gene_info ⛔どこからとってきた？

		// class GeneInfoRecord {
		// 	String geneId;
		// 	String symbol;
		// 	LinkedHashSet<String> synonyms = new LinkedHashSet<String>();
		// 	String hgncId;
		// 	String mimId;
		// 	String mapLocation;
		// 	String description;
		// 	String typeOfGene;
		// 	String otherDesignations;
		// 	String summary;
		// }
		LinkedHashMap<String, GeneInfoRecord> geneMap = loadGeneInfoRecords(
				// ncbigene.file.path
				DiseaseGeneAssociationUtil.NCBI_GENE_INFO_PATH,
				geneSummaryMap);
		System.out.println("NCBI gene Count : " + geneMap.size());

		// ttlとして書き出す
		writeAllGeneTtl(OUTPUT_PATH, geneMap);
	}

	/** キャッシュ済みの summary ファイルがあれば読み込み、なければ NCBI CLI で summary を準備する。 */ ✅
	// gene_summary.tsvを読み取って以下を返す
	// {gene_id: abstract}
	// 例: {7157: This gene encodes a tumor suppressor protein containing transcriptional activation, DNA binding, and oligomerization domains. The encoded protein responds to diverse cellular stresses to regulate expression of target genes, thereby inducing cell cycle arrest, apoptosis, senescence, DNA repair, or changes in metabolism. Mutations in this gene are associated with a variety of human cancers, including hereditary cancers such as Li-Fraumeni syndrome. Alternative splicing of this gene and the use of alternate promoters result in multiple transcript variants and isoforms. Additional isoforms have also been shown to result from the use of alternate translation initiation codons from identical transcript variants (PMIDs: 12032546, 20937277). [provided by RefSeq, Dec 2016]}
	private static LinkedHashMap<String, String> loadGeneSummaryMap() throws IOException, InterruptedException {
		String summaryPath = resolveSummaryPath();
		if (summaryPath != null) {
			return loadGeneSummaryMapFromTsv(summaryPath);
		}
		return loadGeneSummaryMapFromDatasets();
	}

	/** 設定値と latest 規則を使って summary ファイルのパスを求める。 */ ✅
	// ene_summary.tsv.gz
	private static String resolveSummaryPath() {
		// ncbigene.summary.path
		String configuredSummaryPath = RdfBuildSupport.trimToNull(CONFIG.getProperty(SUMMARY_PATH_KEY));
		if (configuredSummaryPath != null) {
			Path configuredPath = Paths.get(configuredSummaryPath);
			if (Files.exists(configuredPath)) {
				return configuredPath.toString();
			}
		}

		Path baseDir = RdfBuildSupport.resolveResourceRoot(CONFIG, NCBI_GENE_DIR_KEY);
		Path resolved = RdfBuildSupport.resolveLatestFile(baseDir, "gene_summary.tsv.gz", false);
		if (resolved != null) {
			return resolved.toString();
		}

		resolved = RdfBuildSupport.resolveLatestFile(baseDir, "gene_summary.tsv", false);
		if (resolved != null) {
			return resolved.toString();
		}
		return null;
	}

	// ✅
	// gene_summary.tsvを読み取って以下を返す
	// {gene_id: abstract}
	// 例: {7157: This gene encodes a tumor suppressor protein containing transcriptional activation, DNA binding, and oligomerization domains. The encoded protein responds to diverse cellular stresses to regulate expression of target genes, thereby inducing cell cycle arrest, apoptosis, senescence, DNA repair, or changes in metabolism. Mutations in this gene are associated with a variety of human cancers, including hereditary cancers such as Li-Fraumeni syndrome. Alternative splicing of this gene and the use of alternate promoters result in multiple transcript variants and isoforms. Additional isoforms have also been shown to result from the use of alternate translation initiation codons from identical transcript variants (PMIDs: 12032546, 20937277). [provided by RefSeq, Dec 2016]}
	private static LinkedHashMap<String, String> loadGeneSummaryMapFromTsv(String path) throws IOException {
		LinkedHashMap<String, String> geneSummaryMap = new LinkedHashMap<String, String>();
		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t", -1);
				// https://qiita.com/YanHengGo/items/e315986bb2f549f4f685
				// 数字マッチしていたら
				if (split.length > 1 && split[0].matches("\\d+")) {
					geneSummaryMap.put(split[0], split[1]);
				}
				else if (split.length > 2 && split[1].matches("\\d+")) {
					geneSummaryMap.put(split[1], split[2]);
				}
			}
		}
		return geneSummaryMap;
	}

	// 多分NCBIGeneSummaryHelper.javaでncbi cliからデータをとってきているのと同じ✅
	private static LinkedHashMap<String, String> loadGeneSummaryMapFromDatasets() throws IOException, InterruptedException {
		String datasetsPath = RdfBuildSupport.resolveExecutablePath(CONFIG, DATASETS_PATH_KEY, "datasets.exe");
		String dataformatPath = RdfBuildSupport.resolveExecutablePath(CONFIG, DATAFORMAT_PATH_KEY, "dataformat.exe");

		Process datasetsProcess = new ProcessBuilder(
				datasetsPath,
				"summary",
				"gene",
				"taxon",
				"human",
				"--as-json-lines",
				"--limit",
				"all")
				.directory(Paths.get(".").toFile())
				.start();

		Process dataformatProcess = new ProcessBuilder(
				dataformatPath,
				"tsv",
				"gene",
				"--fields",
				"symbol,gene-id,summary-description")
				.directory(Paths.get(".").toFile())
				.start();

		ByteArrayOutputStream datasetsError = new ByteArrayOutputStream();
		ByteArrayOutputStream dataformatError = new ByteArrayOutputStream();

		Thread pumpThread = startPipeThread(datasetsProcess.getInputStream(), dataformatProcess.getOutputStream());
		Thread datasetsErrorThread = startPipeThread(datasetsProcess.getErrorStream(), datasetsError);
		Thread dataformatErrorThread = startPipeThread(dataformatProcess.getErrorStream(), dataformatError);

		LinkedHashMap<String, String> geneSummaryMap = new LinkedHashMap<String, String>();
		try (BufferedReader reader = new BufferedReader(new InputStreamReader(dataformatProcess.getInputStream()))) {
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t", -1);
				if (split.length > 1 && split[0].matches("\\d+")) {
					geneSummaryMap.put(split[0], split[1]);
				}
			}
		}

		int datasetsExit = datasetsProcess.waitFor();
		pumpThread.join();
		int dataformatExit = dataformatProcess.waitFor();
		datasetsErrorThread.join();
		dataformatErrorThread.join();

		if (datasetsExit != 0) {
			throw new IOException("datasets.exe failed: " + datasetsError.toString().trim());
		}
		if (dataformatExit != 0) {
			throw new IOException("dataformat.exe failed: " + dataformatError.toString().trim());
		}

		return geneSummaryMap;
	}

	private static Thread startPipeThread(InputStream input, OutputStream output) {
		Thread thread = new Thread(() -> {
			try (InputStream in = input; OutputStream out = output) {
				in.transferTo(out);
			}
			catch (IOException e) {
				throw new RuntimeException(e);
			}
		});
		thread.setDaemon(true);
		thread.start();
		return thread;
	}

	// ncbigene.file.pathとsummaryをくっつける✅
	private static LinkedHashMap<String, GeneInfoRecord> loadGeneInfoRecords(
			String geneInfoPath,
			LinkedHashMap<String, String> geneSummaryMap) throws IOException {
		LinkedHashMap<String, GeneInfoRecord> geneMap = new LinkedHashMap<String, GeneInfoRecord>();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(geneInfoPath)) {
			reader.readLine();
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t", -1);
				if (split.length <= 13) {
					continue;
				}

				// class GeneInfoRecord {
				// 	String geneId;
				// 	String symbol;
				// 	LinkedHashSet<String> synonyms = new LinkedHashSet<String>();
				// 	String hgncId;
				// 	String mimId;
				// 	String mapLocation;
				// 	String description;
				// 	String typeOfGene;
				// 	String otherDesignations;
				// 	String summary;
				// }

				GeneInfoRecord gene = new GeneInfoRecord();
				gene.geneId = split[1];
				gene.symbol = split[2];
				gene.synonyms = parsePipeSeparatedValues(split[4]);


				// private static void parseDbXrefs(String dbXrefs, GeneInfoRecord gene) {
				// 	if (dbXrefs == null || dbXrefs.equals("-")) {
				// 		return;
				// 	}
				// 
				// 	for (String ref : dbXrefs.split("\\|")) {
				// 		if (ref.startsWith("HGNC:HGNC:")) {
				// 			gene.hgncId = ref.substring("HGNC:HGNC:".length());
				// 		}
				// 		else if (ref.startsWith("HGNC:")) {
				// 			gene.hgncId = ref.substring("HGNC:".length()).replace("HGNC:", "");
				// 		}
				// 		else if (ref.startsWith("MIM:")) {
				// 			gene.mimId = ref.substring("MIM:".length());
				// 		}
				// 	}
				// }

				// いくつかのIDがパイプされている文字列から、HGNC: などのプレフィックスを省いてgene.hgncIdやmimiIdに入れていく
				parseDbXrefs(split[5], gene);
				gene.mapLocation = normalizeDash(split[7]);
				gene.description = normalizeDash(split[8]);
				gene.typeOfGene = normalizeDash(split[9]);
				gene.otherDesignations = normalizeDash(split[13]);
				gene.summary = normalizeDash(geneSummaryMap.get(gene.geneId));

				geneMap.put(gene.geneId, gene);
			}
		}

		return geneMap;
	}

	private static LinkedHashSet<String> parsePipeSeparatedValues(String value) {
		LinkedHashSet<String> values = new LinkedHashSet<String>();
		if (value == null || value.equals("-") || value.isEmpty()) {
			return values;
		}

		for (String part : value.split("\\|")) {
			if (!part.isEmpty() && !part.equals("-")) {
				values.add(part);
			}
		}
		return values;
	}

	private static void parseDbXrefs(String dbXrefs, GeneInfoRecord gene) {
		if (dbXrefs == null || dbXrefs.equals("-")) {
			return;
		}

		for (String ref : dbXrefs.split("\\|")) {
			if (ref.startsWith("HGNC:HGNC:")) {
				gene.hgncId = ref.substring("HGNC:HGNC:".length());
			}
			else if (ref.startsWith("HGNC:")) {
				gene.hgncId = ref.substring("HGNC:".length()).replace("HGNC:", "");
			}
			else if (ref.startsWith("MIM:")) {
				gene.mimId = ref.substring("MIM:".length());
			}
		}
	}

	private static String normalizeDash(String value) {
		String normalized = RdfBuildSupport.trimToNull(value);
		return normalized != null ? normalized : "-";
	}

	private static String escapeLiteral(String value) {
		if (value == null) {
			return "";
		}
		return value.replace("\\", "\\\\").replace("\"", "\\\"");
	}

	private static void writeAllGeneTtl(String outputPath, LinkedHashMap<String, GeneInfoRecord> geneMap) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX hgnc: <https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:>"); writer.newLine();
			writer.write("PREFIX ncbigene: <http://identifiers.org/ncbigene/>"); writer.newLine();
			writer.write("PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>"); writer.newLine();
			writer.write("PREFIX med2rdf: <http://med2rdf.org/ontology/>"); writer.newLine();
			writer.write("PREFIX mim: <https://omim.org/entry/>"); writer.newLine();
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();
			writer.write("PREFIX sio: <http://semanticscience.org/resource/>"); writer.newLine();
			writer.write("PREFIX nuc: <http://ddbj.nig.ac.jp/ontologies/nucleotide/>"); writer.newLine();
			writer.write("PREFIX hop: <http://purl.org/net/orthordf/hOP/ontology#>"); writer.newLine();

			for (GeneInfoRecord gene : geneMap.values()) {
				writer.write("ncbigene:" + gene.geneId); writer.newLine();
				if (!gene.synonyms.isEmpty()) {
					writer.write("    nuc:gene_synonym ");
					writeQuotedList(writer, gene.synonyms);
					writer.write(" ;");
					writer.newLine();
				}
				if (!"-".equals(gene.mapLocation)) {
					writer.write("    nuc:map \"" + escapeLiteral(gene.mapLocation) + "\" ;");
					writer.newLine();
				}
				if (!"-".equals(gene.otherDesignations)) {
					writer.write("    dcterms:alternative \"" + escapeLiteral(gene.otherDesignations) + "\" ;");
					writer.newLine();
				}
				if (gene.hgncId != null) {
					writer.write("    sio:SIO_000205 hgnc:" + gene.hgncId + " ;");
					writer.newLine();
				}
				if (gene.mimId != null) {
					writer.write("    rdfs:seeAlso mim:" + gene.mimId + " ;");
					writer.newLine();
				}
				if (!"-".equals(gene.summary)) {
					writer.write("    obo:NCIT_C42581 \"" + escapeLiteral(gene.summary) + "\" ;");
					writer.newLine();
				}

				writer.write("    dcterms:identifier \"" + escapeLiteral(gene.geneId) + "\" ;"); writer.newLine();
				writer.write("    rdfs:label \"" + escapeLiteral(gene.symbol) + "\" ;"); writer.newLine();
				writer.write("    dcterms:description \"" + escapeLiteral(gene.description) + "\" ;"); writer.newLine();
				writer.write("    hop:typeOfGene \"" + escapeLiteral(gene.typeOfGene) + "\" ;"); writer.newLine();
				writer.write("    a med2rdf:Gene, ncit:C16612 ."); writer.newLine();

				if (gene.hgncId != null) {
					writer.write("hgnc:" + gene.hgncId); writer.newLine();
					writer.write("    a ncit:C43568 ;"); writer.newLine();
					writer.write("    rdfs:label \"" + escapeLiteral(gene.symbol) + "\" ."); writer.newLine();
				}
			}
		}
	}

	private static void writeQuotedList(BufferedWriter writer, LinkedHashSet<String> values) throws IOException {
		int index = 0;
		int size = values.size();
		for (String value : values) {
			index++;
			writer.write("\"" + escapeLiteral(value) + "\"");
			if (index < size) {
				writer.write(", ");
			}
		}
	}
}
