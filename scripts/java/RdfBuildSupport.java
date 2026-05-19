package pubcasefinder_260415;

	import java.io.BufferedWriter;
	import java.io.BufferedReader;
	import java.io.IOException;
	import java.io.InputStream;
	import java.io.InputStreamReader;
	import java.io.OutputStream;
	import java.io.OutputStreamWriter;
	import java.nio.charset.StandardCharsets;
	import java.nio.file.Files;
	import java.nio.file.Path;
	import java.nio.file.Paths;
	import java.util.LinkedHashMap;
	import java.util.List;
	import java.util.Comparator;

	// .propatiesとかの外部ファイルに設定値などをかき出す仕組み
	import java.util.Properties;
	import java.util.stream.Collectors;
	import java.util.stream.Stream;
	import java.util.zip.GZIPInputStream;
	import java.util.zip.GZIPOutputStream;

// RDF 生成器が共通利用する設定、パス解決、gzip 入力ユーティリティ
public final class RdfBuildSupport {
	public static final String CONFIG_PATH = "pcf-rdf.properties";

	private RdfBuildSupport() {
	}

/** 設定ファイルを読み込み、パス override 値をメモリに取り込む。 */
	public static Properties loadConfig() {
		Properties properties = new Properties();
		Path configPath = Paths.get(CONFIG_PATH);
		if (Files.exists(configPath)) {
			// ファイルを開き、そのファイルから読み取る入力ストリームを返します。
			try (InputStream input = Files.newInputStream(configPath)) {
				// configPathを読み取ってバッファリング
				properties.load(input);
			}
			catch (IOException e) {
				throw new RuntimeException("Failed to load config: " + configPath, e);
			}
		}
		return properties;
	}

/** 空の設定文字列を null に変換する。 */
	public static String trimToNull(String value) {
		if (value == null) {
			return null;
		}
		String trimmed = value.trim();
		return trimmed.isEmpty() ? null : trimmed;
	}

/** パス区切り文字をスラッシュ基準に統一する。 */
	public static String normalizePath(String value) {
		return value.replace('\\', '/');
	}

/** 設定値または既定値を使って RDF 出力ディレクトリを決定する。 */
	public static String resolveConfiguredOutputDir(Properties config) {
		String configuredDir = trimToNull(config.getProperty("rdf.output.dir"));
		if (configuredDir != null) {
			return normalizePath(configuredDir);
		}
		return "RDF/latest";
	}

/** 個別ファイル override または latest 規則を使って入力ファイルのパスを決定する。 */
	public static String resolveConfiguredFile(Properties config, String exactPathKey, Path baseDir, String fileName) {
		// 結果が空文字列になったとき、nullを返す
		// https://java-tech-copa.com/2024/08/29/java%EF%BD%9Cstringutils%E3%81%AEtrim%E3%80%81trimtoempty%E3%80%81trimtonull%E3%83%A1%E3%82%BD%E3%83%83%E3%83%89/
		//
		// configは多分PCF_RDF.zipを読み取ってロードする
		// private static final Properties CONFIG = RdfBuildSupport.loadConfig();
		String exactPath = trimToNull(config.getProperty(exactPathKey));
		if (exactPath != null) {
			// 相対パスの./とかを取り除いてくれている
			// https://www.javadrive.jp/start/file/index15.html
			return normalizePath(exactPath);
		}
		return resolveLatestFile(baseDir, fileName, true).toString().replace('\\', '/');
	}

/** ディレクトリキーに対応する既定のデータルートパスを返す。 */
	public static Path resolveResourceRoot(Properties config, String directoryKey) {
		String configuredDir = trimToNull(config.getProperty(directoryKey));
		if (configuredDir != null) {
			return Paths.get(normalizePath(configuredDir));
		}
		return resolveDefaultResourceRoot(directoryKey);
	}

	private static Path resolveDefaultResourceRoot(String directoryKey) {
		switch (directoryKey) {
		case "ncbigene.dir":
			return Paths.get("data", "NCBIGene");
		case "medgen.dir":
			return Paths.get("data", "MedGen");
		case "orphanet.dir":
			return Paths.get("data", "Orphanet");
		case "mondo.dir":
			return Paths.get("data", "MONDO");
		case "gencc.dir":
			return Paths.get("data", "GenCC");
		case "panelsearch.dir":
			return Paths.get("data", "PanelSearch");
		case "omim.dir":
			return Paths.get("data", "OMIM");
		case "kegg.dir":
			return Paths.get("data", "KEGG");
		case "genereviews.dir":
			return Paths.get("data", "GeneReviews");
		case "hpo.dir":
			return Paths.get("data", "HPO");
		default:
			throw new IllegalArgumentException("Unknown directory key: " + directoryKey);
		}
	}

/** direct/latest/最新日付フォルダの順で対象ファイルを探索する。 */✅
	public static Path resolveLatestFile(Path baseDir, String fileName, boolean required) {
		Path directFile = baseDir.resolve(fileName);
		if (Files.exists(directFile)) {
			return directFile;
		}

		Path latestFile = baseDir.resolve("latest").resolve(fileName);
		if (Files.exists(latestFile)) {
			return latestFile;
		}

		if (!Files.isDirectory(baseDir)) {
			if (required) {
				throw new IllegalStateException("Could not find " + fileName + " under " + baseDir);
			}
			return null;
		}

		try (Stream<Path> children = Files.list(baseDir)) {
			Path resolved = children
					.filter(Files::isDirectory)
					.sorted(Comparator.comparing((Path path) -> path.getFileName().toString()).reversed())
					.map(path -> path.resolve(fileName))
					.filter(Files::exists)
					.findFirst()
					.orElse(null);
			if (resolved == null && required) {
				throw new IllegalStateException("Could not find " + fileName + " under " + baseDir);
			}
			return resolved;
		}
		catch (IOException e) {
			throw new RuntimeException("Failed to resolve latest file for " + fileName + " under " + baseDir, e);
		}
	}

/** ファイル拡張子に応じて通常入力または gzip 入力ストリームを開く。 */
	public static InputStream openMaybeGzip(String path) throws IOException {
		InputStream input = Files.newInputStream(Paths.get(path));
		return path.endsWith(".gz") ? new GZIPInputStream(input) : input;
	}

/** UTF-8 で通常入力/圧縮入力ファイルを読む BufferedReader を開く。 */
	public static BufferedReader openUtf8Reader(String path) throws IOException {
		return new BufferedReader(new InputStreamReader(openMaybeGzip(path), StandardCharsets.UTF_8));
	}

/** 出力ファイルの親ディレクトリが存在しなければ作成する。 */
	public static void ensureParentDirectory(String outputPath) throws IOException {
		Path parent = Paths.get(outputPath).getParent();
		if (parent != null) {
			Files.createDirectories(parent);
		}
	}

/** ファイル拡張子に応じて UTF-8 通常出力または UTF-8 gzip 出力を開く。 */
	// 出力先と文字コードを決める？✅
	public static BufferedWriter createBufferedWriter(String outputPath) throws IOException {
		ensureParentDirectory(outputPath);
		// ファイルを開くか作成して、そのファイルにバイトを書き込むために使用できる出力ストリームを返します。
		OutputStream output = Files.newOutputStream(Paths.get(outputPath));
		if (outputPath.endsWith(".gz")) {
			// このクラスは、GZIPファイル形式で圧縮されたデータを書き込むためのストリーム・フィルタを実装します。
			output = new GZIPOutputStream(output);
		}

		// OutputStreamWriter(OutputStream out, Charset cs)	与えられた文字セットを使うOutputStreamWriterを作成します。
		// 文字をバッファリングすることによって、文字、配列、または文字列を効率良く文字型出力ストリームに書き込みます。
		return new BufferedWriter(new OutputStreamWriter(output, StandardCharsets.UTF_8));
	}

/** 設定値、同梱 tools フォルダ、浅いファイル探索の順で実行ファイルのパスを決定する。 */
	public static String resolveExecutablePath(Properties config, String configKey, String fileName) throws IOException {
		String configured = trimToNull(config.getProperty(configKey));
		if (configured != null && Files.exists(Paths.get(configured))) {
			return Paths.get(configured).toString();
		}

		Path bundledTool = Paths.get("tools", "ncbi", fileName);
		if (Files.exists(bundledTool)) {
			return bundledTool.toAbsolutePath().normalize().toString();
		}

		List<Path> matches;
		try (Stream<Path> paths = Files.walk(Paths.get("."), 4)) {
			matches = paths
					.filter(path -> Files.isRegularFile(path) && path.getFileName().toString().equalsIgnoreCase(fileName))
					.collect(Collectors.toList());
		}

		if (matches.isEmpty()) {
			throw new IOException("Could not find " + fileName + ". Set " + configKey + " in " + CONFIG_PATH + " if needed.");
		}
		return matches.get(0).toAbsolutePath().normalize().toString();
	}

/** 文字列の組を順序保持マップとして構築する。 */
	public static LinkedHashMap<String, String> createStringMap(String... keyValuePairs) {
		if (keyValuePairs.length % 2 != 0) {
			throw new IllegalArgumentException("Key/value pairs must be even.");
		}

		LinkedHashMap<String, String> map = new LinkedHashMap<String, String>();
		for (int i = 0; i < keyValuePairs.length; i += 2) {
			map.put(keyValuePairs[i], keyValuePairs[i + 1]);
		}
		return map;
	}
}
