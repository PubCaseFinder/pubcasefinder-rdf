package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.util.Properties;

// all_gene.ttl 생성을 보조하는 NCBI gene summary 준비 유틸리티
public class NCBIGeneSummaryHelper {
	private static final Properties CONFIG = RdfBuildSupport.loadConfig();
	private static final String OUTPUT_PATH_KEY = "ncbigene.summary.path";
	private static final String DATASETS_PATH_KEY = "ncbigene.datasets.path";
	private static final String DATAFORMAT_PATH_KEY = "ncbigene.dataformat.path";
	private static final String DEFAULT_OUTPUT_PATH = "data/NCBIGene/latest/gene_summary.tsv";

	/** 실행 인자를 해석해 gene summary 캐시 파일을 생성한다. */
	public static void main(String[] args) throws Exception {
		String outputPath = resolveOutputPath(args);
		writeGeneSummaryFile(outputPath);
		System.out.println("gene_summary output : " + outputPath);
	}

	/** 실행 인자와 설정값을 기준으로 summary 출력 경로를 결정한다. */
	private static String resolveOutputPath(String[] args) {
		if (args != null && args.length > 0 && args[0] != null && !args[0].isBlank()) {
			return args[0];
		}
		String configured = RdfBuildSupport.trimToNull(CONFIG.getProperty(OUTPUT_PATH_KEY));
		return configured != null ? configured : DEFAULT_OUTPUT_PATH;
	}

	/** NCBI CLI를 호출해 gene summary를 추출하고 TSV 또는 TSV.GZ로 저장한다. */
	private static void writeGeneSummaryFile(String outputPath) throws IOException, InterruptedException {
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
				.directory(java.nio.file.Paths.get(".").toFile())
				.start();

		Process dataformatProcess = new ProcessBuilder(
				dataformatPath,
				"tsv",
				"gene",
				"--fields",
				"gene-id,summary-description")
				.directory(java.nio.file.Paths.get(".").toFile())
				.start();

		ByteArrayOutputStream datasetsError = new ByteArrayOutputStream();
		ByteArrayOutputStream dataformatError = new ByteArrayOutputStream();
		Thread pumpThread = startPipeThread(datasetsProcess.getInputStream(), dataformatProcess.getOutputStream());
		Thread datasetsErrorThread = startPipeThread(datasetsProcess.getErrorStream(), datasetsError);
		Thread dataformatErrorThread = startPipeThread(dataformatProcess.getErrorStream(), dataformatError);

		try (BufferedReader reader = new BufferedReader(new InputStreamReader(dataformatProcess.getInputStream()));
				BufferedWriter writer = createWriter(outputPath)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t", -1);
				if (split.length > 1 && split[0].matches("\\d+")) {
					writer.write(split[0]);
					writer.write('\t');
					writer.write(split[1]);
					writer.newLine();
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
	}

	private static BufferedWriter createWriter(String outputPath) throws IOException {
		return RdfBuildSupport.createBufferedWriter(outputPath);
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

}
