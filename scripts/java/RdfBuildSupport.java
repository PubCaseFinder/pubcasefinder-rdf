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
	import java.util.Properties;
	import java.util.stream.Collectors;
	import java.util.stream.Stream;
	import java.util.zip.GZIPInputStream;
	import java.util.zip.GZIPOutputStream;

// RDF 생성기들이 공통으로 사용하는 설정, 경로 해석, gzip 입력 유틸리티
public final class RdfBuildSupport {
	public static final String CONFIG_PATH = "pcf-rdf.properties";

	private RdfBuildSupport() {
	}

	/** 설정 파일을 읽어 경로 override 값을 메모리에 적재한다. */
	public static Properties loadConfig() {
		Properties properties = new Properties();
		Path configPath = Paths.get(CONFIG_PATH);
		if (Files.exists(configPath)) {
			try (InputStream input = Files.newInputStream(configPath)) {
				properties.load(input);
			}
			catch (IOException e) {
				throw new RuntimeException("Failed to load config: " + configPath, e);
			}
		}
		return properties;
	}

	/** 비어 있는 설정 문자열을 null로 바꾼다. */
	public static String trimToNull(String value) {
		if (value == null) {
			return null;
		}
		String trimmed = value.trim();
		return trimmed.isEmpty() ? null : trimmed;
	}

	/** 경로 구분자를 슬래시 기준으로 통일한다. */
	public static String normalizePath(String value) {
		return value.replace('\\', '/');
	}

	/** 설정값 또는 기본값을 사용해 RDF 출력 디렉터리를 결정한다. */
	public static String resolveConfiguredOutputDir(Properties config) {
		String configuredDir = trimToNull(config.getProperty("rdf.output.dir"));
		if (configuredDir != null) {
			return normalizePath(configuredDir);
		}
		return "RDF/latest";
	}

	/** 개별 파일 override 또는 latest 규칙을 이용해 입력 파일 경로를 결정한다. */
	public static String resolveConfiguredFile(Properties config, String exactPathKey, Path baseDir, String fileName) {
		String exactPath = trimToNull(config.getProperty(exactPathKey));
		if (exactPath != null) {
			return normalizePath(exactPath);
		}
		return resolveLatestFile(baseDir, fileName, true).toString().replace('\\', '/');
	}

	/** 디렉터리 키에 대응하는 기본 데이터 루트 경로를 반환한다. */
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

	/** direct/latest/최신 날짜 폴더 순서로 대상 파일을 탐색한다. */
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

	/** 파일 확장자에 따라 일반 입력 또는 gzip 입력 스트림을 연다. */
	public static InputStream openMaybeGzip(String path) throws IOException {
		InputStream input = Files.newInputStream(Paths.get(path));
		return path.endsWith(".gz") ? new GZIPInputStream(input) : input;
	}

	/** UTF-8 기준으로 일반/압축 입력 파일을 읽는 BufferedReader를 연다. */
	public static BufferedReader openUtf8Reader(String path) throws IOException {
		return new BufferedReader(new InputStreamReader(openMaybeGzip(path), StandardCharsets.UTF_8));
	}

	/** 출력 파일의 상위 디렉터리가 없으면 생성한다. */
	public static void ensureParentDirectory(String outputPath) throws IOException {
		Path parent = Paths.get(outputPath).getParent();
		if (parent != null) {
			Files.createDirectories(parent);
		}
	}

	/** 파일 확장자에 따라 UTF-8 일반 출력 또는 UTF-8 gzip 출력을 연다. */
	public static BufferedWriter createBufferedWriter(String outputPath) throws IOException {
		ensureParentDirectory(outputPath);
		OutputStream output = Files.newOutputStream(Paths.get(outputPath));
		if (outputPath.endsWith(".gz")) {
			output = new GZIPOutputStream(output);
		}
		return new BufferedWriter(new OutputStreamWriter(output, StandardCharsets.UTF_8));
	}

	/** 설정값, 번들 tools 폴더, 얕은 파일 탐색 순서로 실행 파일 경로를 결정한다. */
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

	/** 문자열 쌍을 순서가 보존되는 맵으로 만든다. */
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
