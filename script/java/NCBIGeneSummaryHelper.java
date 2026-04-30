package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.util.Properties;

// all_gene.ttl の生成を補助する NCBI gene summary 準備ユーティリティ
public class NCBIGeneSummaryHelper {
	private static final Properties CONFIG = RdfBuildSupport.loadConfig();
	private static final String OUTPUT_PATH_KEY = "ncbigene.summary.path";
	private static final String DATASETS_PATH_KEY = "ncbigene.datasets.path";
	private static final String DATAFORMAT_PATH_KEY = "ncbigene.dataformat.path";
	private static final String DEFAULT_OUTPUT_PATH = "data/NCBIGene/latest/gene_summary.tsv";

/** 実行引数を解釈して gene summary のキャッシュファイルを生成する。 */
	public static void main(String[] args) throws Exception {
		// outputファイルを設定
		String outputPath = resolveOutputPath(args);

		// ncbiからデータを取得して、data/NCBIGene/latest/gene_summary.tsvに配置する
		writeGeneSummaryFile(outputPath);
		System.out.println("gene_summary output : " + outputPath);
	}

/** 実行引数と設定値に基づいて summary の出力パスを決定する。 */✅
	private static String resolveOutputPath(String[] args) {
		// 引数が入っていれば引数の最初の要素を返す
		if (args != null && args.length > 0 && args[0] != null && !args[0].isBlank()) {
			return args[0];
		}

		// 設定値に`ncbigene.summary.path`が入っていなければその値を返すし、そうでなければ`data/NCBIGene/latest/gene_summary.tsv`を返す
		String configured = RdfBuildSupport.trimToNull(CONFIG.getProperty(OUTPUT_PATH_KEY));
		return configured != null ? configured : DEFAULT_OUTPUT_PATH;
	}

/** NCBI CLI を呼び出して gene summary を抽出し、TSV または TSV.GZ として保存する。 */
	// NCBI CLIを通してjsonファイルを
	// https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/download-and-install/
	private static void writeGeneSummaryFile(String outputPath) throws IOException, InterruptedException {
		String datasetsPath = RdfBuildSupport.resolveExecutablePath(CONFIG, DATASETS_PATH_KEY, "datasets.exe");
		String dataformatPath = RdfBuildSupport.resolveExecutablePath(CONFIG, DATAFORMAT_PATH_KEY, "dataformat.exe");

		// datasets.exeに引数をつけて実行
		Process datasetsProcess = new ProcessBuilder(
				datasetsPath,
				"summary",
				"gene",
				"taxon",
				"human",
				"--as-json-lines",
				"--limit",
				"all")
				// 作業ディレクトリを示す
				.directory(java.nio.file.Paths.get(".").toFile())
				.start();

		// dataformat.exeに引数をつけて実行
		// https://www.ncbi.nlm.nih.gov/datasets/docs/v2/command-line-tools/using-dataformat/gene-data-reports/
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

		// https://qiita.com/mitsumizo/items/836ce2e00e91c33fcf95
		// osで実行したプロセスの標準出力をinputに、出力先をoutputにしている
		// サブプロセスの通常の入力に接続された出力ストリームを返します。 ストリームへの出力は、このProcessオブジェクトが表すプロセスの標準入力に渡されます。
		// 標準出力を出力ストリームとしていた場合は標準出力に返す
		// ここではdatasetsコマンドの出力をdataformatコマンドの入力につなぐ
		// パイプする主体はjavaなので、javaからみて入力ストリームはgetInputStream、javaから見て出力ストリームはgetOutputStream
		Thread pumpThread = startPipeThread(datasetsProcess.getInputStream(), dataformatProcess.getOutputStream());
		Thread datasetsErrorThread = startPipeThread(datasetsProcess.getErrorStream(), datasetsError);
		Thread dataformatErrorThread = startPipeThread(dataformatProcess.getErrorStream(), dataformatError);

		try (BufferedReader reader = new BufferedReader(new InputStreamReader(dataformatProcess.getInputStream()));

				// private static BufferedWriter createWriter(String outputPath) throws IOException {
				// 	return RdfBuildSupport.createBufferedWriter(outputPath);
				// }

				// public static BufferedWriter createBufferedWriter(String outputPath) throws IOException {
				// 	ensureParentDirectory(outputPath);
				// 	// ファイルを開くか作成して、そのファイルにバイトを書き込むために使用できる出力ストリームを返します。
				// 	OutputStream output = Files.newOutputStream(Paths.get(outputPath));
				// 	if (outputPath.endsWith(".gz")) {
				// 		// このクラスは、GZIPファイル形式で圧縮されたデータを書き込むためのストリーム・フィルタを実装します。
				// 		output = new GZIPOutputStream(output);
				// 	}

				// 	// OutputStreamWriter(OutputStream out, Charset cs)	与えられた文字セットを使うOutputStreamWriterを作成します。
				// 	// 文字をバッファリングすることによって、文字、配列、または文字列を効率良く文字型出力ストリームに書き込みます。
				// 	return new BufferedWriter(new OutputStreamWriter(output, StandardCharsets.UTF_8));
				// }

				// 書く対象のアウトプットストリームを作っている
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

	// 処理の出力を任意の場所に書き出すやつ✅
	private static Thread startPipeThread(InputStream input, OutputStream output) {
		Thread thread = new Thread(() -> {
			try (InputStream in = input; OutputStream out = output) {
				// 	この入力ストリームからすべてのバイトを読み込んで、指定された出力ストリームに読み込まれた順序でバイトを書き込みます。
				// 多分実行した結果をoutputファイルに入れていくってことだと思う
				in.transferTo(out);
			}
			catch (IOException e) {
				// https://it-kyujin.jp/article/detail/511/
				throw new RuntimeException(e);
			}
		});
		// thread.setDaemonはデーモンスレッドにセットしているので、メイン処理が完了すれば監視スレッドも自動的に消える
		// ユーザースレッドにする場合は、これが一つでも動いている場合はプログラムが終了できなくなる
		// でもこの作業をデーモンスレッドにする必要なさそう
		thread.setDaemon(true);
		thread.start();
		return thread;
	}

}
