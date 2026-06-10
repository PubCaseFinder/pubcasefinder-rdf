package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Properties;

// 상속 용어집과 공식 라벨 테이블을 결합해 일본어 HPO 라벨 RDF를 생성한다.
public class HP_ja {
	private static final Properties CONFIG = RdfBuildSupport.loadConfig();
	private static final String HPO_INHERITANCE_JA_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "hpo.inheritance.ja.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "hpo.dir"), "HPO_Inheritance_en_jp.txt");
	private static final String HPO_JAPANESE_LABEL_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "hpo.japanese.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "hpo.dir"), "HPO-japanese.alpha.21Jul2023.tsv");
	private static final String RDF_DIR = RdfBuildSupport.resolveConfiguredOutputDir(CONFIG);
	private static final String OUTPUT_PATH = RDF_DIR + "/HPO_ja.ttl";

	private static final String PREFIX_OBO = "PREFIX obo: <http://purl.obolibrary.org/obo/>";
	private static final String PREFIX_RDFS = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>";

	public static void main(String[] args) throws IOException {
		Path inheritanceFile = args.length > 0 ? Paths.get(args[0]) : Paths.get(HPO_INHERITANCE_JA_PATH);
		Path japaneseFile = args.length > 1 ? Paths.get(args[1]) : Paths.get(HPO_JAPANESE_LABEL_PATH);
		Path outputFile = args.length > 2 ? Paths.get(args[2]) : Paths.get(OUTPUT_PATH);

		validateInputFile(inheritanceFile);
		validateInputFile(japaneseFile);
		createParentDirectories(outputFile);

		Map<String, String> labels = new LinkedHashMap<String, String>();

		int inheritanceCount = loadInheritanceLabels(inheritanceFile, labels);
		int officialCount = loadOfficialJapaneseLabels(japaneseFile, labels);
		writeTurtle(outputFile, labels);

		System.out.println("Inheritance labels loaded: " + inheritanceCount);
		System.out.println("Official labels loaded: " + officialCount);
		System.out.println("Unique labels written: " + labels.size());
		System.out.println("Output: " + outputFile.toAbsolutePath());
	}

	private static void validateInputFile(Path path) throws IOException {
		if (!Files.exists(path) || !Files.isRegularFile(path)) {
			throw new IOException("Input file not found: " + path.toAbsolutePath());
		}
	}

	private static void createParentDirectories(Path outputFile) throws IOException {
		RdfBuildSupport.ensureParentDirectory(outputFile.toString());
	}

	private static int loadInheritanceLabels(Path path, Map<String, String> labels) throws IOException {
		int count = 0;

		try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				String[] columns = line.split("\t", -1);
				if (columns.length < 3) {
					continue;
				}

				String hpoId = normalizeHpoId(columns[0]);
				String label = columns[2].trim();
				if (hpoId.isEmpty() || label.isEmpty()) {
					continue;
				}

				labels.put(hpoId, label);
				count++;
			}
		}

		return count;
	}

	private static int loadOfficialJapaneseLabels(Path path, Map<String, String> labels) throws IOException {
		int count = 0;

		try (BufferedReader reader = Files.newBufferedReader(path, StandardCharsets.UTF_8)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				String[] columns = line.split("\t", -1);
				if (columns.length < 14) {
					continue;
				}

				String status = columns[13].trim();
				if (!"OFFICIAL".equals(status)) {
					continue;
				}

				String hpoId = normalizeHpoId(columns[4]);
				String label = columns[7].trim();
				if (hpoId.isEmpty() || label.isEmpty() || "NA".equalsIgnoreCase(label)) {
					continue;
				}

				labels.putIfAbsent(hpoId, label);
				count++;
			}
		}

		return count;
	}

	private static void writeTurtle(Path outputFile, Map<String, String> labels) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputFile.toString())) {
			writer.write(PREFIX_OBO);
			writer.newLine();
			writer.write(PREFIX_RDFS);
			writer.newLine();

			for (Map.Entry<String, String> entry : labels.entrySet()) {
				writer.write("obo:HP_" + entry.getKey() + " rdfs:label \"" + escapeTurtle(entry.getValue()) + "\"@ja .");
				writer.newLine();
			}
		}
	}

	private static String normalizeHpoId(String rawValue) {
		return rawValue.replaceAll("[^0-9]", "");
	}

	private static String escapeTurtle(String value) {
		return value
			.replace("\\", "\\\\")
			.replace("\"", "\\\"");
	}
}
