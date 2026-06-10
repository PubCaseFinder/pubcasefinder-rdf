package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Properties;
import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;
// 질환-유전자 연관 RDF 생성에 필요한 공통 로직을 모은 핵심 유틸리티
public class DiseaseGeneAssociationUtil {
	// 설정 해석, 원본 데이터 로딩, 질환 매핑 확장, TTL 출력을 한곳에서 담당한다.

	public static final String GENCC_SOURCE_URI = "https://search.thegencc.org/download/action/submissions-export-csv";
	public static final String CONFIG_PATH = RdfBuildSupport.CONFIG_PATH;

	private static final Properties CONFIG = RdfBuildSupport.loadConfig();

	public static final String NCBI_GENE_INFO_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "ncbigene.file.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "ncbigene.dir"), "Homo_sapiens.gene_info.gz");
	public static final String MEDGEN_MIM2GENE_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "medgen.mim2gene.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "medgen.dir"), "mim2gene_medgen.txt");
	public static final String ORPHANET_PRODUCT6_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "orphanet.product6.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "orphanet.dir"), "en_product6.xml");
	public static final String MONDO_OWL_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "mondo.owl.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "mondo.dir"), "mondo-international.owl");
	public static final String GENCC_SUBMISSIONS_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "gencc.submissions.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "gencc.dir"), "gencc-submissions.tsv");
	public static final String NANDO_ASSOCIATION_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "panelsearch.association.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "panelsearch.dir"), "nando_gene_association.txt");
	public static final String NANDO_MANUAL_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "panelsearch.manual.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "panelsearch.dir"), "shitei_gene_all_250819.txt");
	public static final String RDF_DIR = RdfBuildSupport.resolveConfiguredOutputDir(CONFIG);

	public static class MergeStats {
		int added;
		int overlap;
	}

	public static class MondoMapping {
		LinkedHashMap<String, LinkedHashSet<String>> mondoToOmim = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, LinkedHashSet<String>> mondoToOrpha = new LinkedHashMap<String, LinkedHashSet<String>>();

		LinkedHashMap<String, LinkedHashSet<String>> omimToMondo = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, LinkedHashSet<String>> orphaToMondo = new LinkedHashMap<String, LinkedHashSet<String>>();
	}

	public static class MondoHierarchy {
		LinkedHashMap<String, LinkedHashSet<String>> parentToChildren = new LinkedHashMap<String, LinkedHashSet<String>>();
	}

	public static class MondoExactMatchMapping {
		LinkedHashMap<String, LinkedHashSet<String>> mondoToOmim = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, LinkedHashSet<String>> mondoToOrpha = new LinkedHashMap<String, LinkedHashSet<String>>();
	}

	public static class GenCCAssociations {
		LinkedHashMap<String, LinkedHashSet<String>> omimAssociations = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, LinkedHashSet<String>> orphanetAssociations = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, LinkedHashSet<String>> mondoAssociations = new LinkedHashMap<String, LinkedHashSet<String>>();
	}

	public static class GenCCSubmissionRecord {
		String genccId;
		String ncbiGeneId;
		String diseaseCurie;
		String classificationTitle;
		String moiCurie;
		String submitterLabel;
	}

	private static final LinkedHashMap<String, String> GENCC_SUBMITTER_LABELS = createGenccSubmitterLabelMap();

	// -----------------------------------------------------------------------------
	// -----------------------------------------------------------------------------

	// -----------------------------------------------------------------------------
	// -----------------------------------------------------------------------------

	public static LinkedHashMap<String, String> loadNcbiGeneSymbolMap(String path) throws IOException {
		LinkedHashMap<String, String> ncbiGeneSymbolMap = new LinkedHashMap<String, String>();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t");
				if (split.length > 2 && !ncbiGeneSymbolMap.containsKey(split[2])) {
					ncbiGeneSymbolMap.put(split[2], split[1]);
				}
			}
		}

		return ncbiGeneSymbolMap;
	}

	public static LinkedHashMap<String, String> loadHgncToNcbiMap(String path) throws IOException {
		LinkedHashMap<String, String> hgncToNcbiMap = new LinkedHashMap<String, String>();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t");
				if (split.length > 5) {
					String dbXrefs = split[5];
					String hgncId = extractHgncId(dbXrefs);
					if (hgncId != null && !hgncToNcbiMap.containsKey(hgncId)) {
						hgncToNcbiMap.put(hgncId, split[1]);
					}
				}
			}
		}

		return hgncToNcbiMap;
	}

	public static ArrayList<GenCCSubmissionRecord> loadGenccSubmissionRecords() throws IOException {
		return loadGenccSubmissionRecords(GENCC_SUBMISSIONS_PATH, NCBI_GENE_INFO_PATH);
	}

	public static ArrayList<GenCCSubmissionRecord> loadGenccSubmissionRecords(String genccSubmissionsPath, String ncbiGeneInfoPath) throws IOException {
		LinkedHashMap<String, String> hgncToNcbiMap = loadHgncToNcbiMap(ncbiGeneInfoPath);
		ArrayList<GenCCSubmissionRecord> records = new ArrayList<GenCCSubmissionRecord>();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(genccSubmissionsPath)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t", -1);
				if (split.length <= 19) {
					continue;
				}

				String genccId = normalizeValue(split[0]);
				String hgncId = normalizeCurieValue(split[1], "HGNC:");
				String diseaseCurie = normalizeValue(split[5]);
				String classificationTitle = normalizeValue(split[8]);
				String moiCurie = normalizeMoiCurie(normalizeValue(split[9]));
				String submitterId = normalizeValue(split[19]);

				if (genccId == null || hgncId == null || diseaseCurie == null || !diseaseCurie.contains(":")) {
					continue;
				}

				String ncbiGeneId = hgncToNcbiMap.get(hgncId);
				if (ncbiGeneId == null) {
					continue;
				}

				GenCCSubmissionRecord record = new GenCCSubmissionRecord();
				record.genccId = genccId;
				record.ncbiGeneId = ncbiGeneId;
				record.diseaseCurie = diseaseCurie;
				record.classificationTitle = classificationTitle;
				record.moiCurie = moiCurie;
				record.submitterLabel = resolveGenccSubmitterLabel(submitterId);
				records.add(record);
			}
		}

		return records;
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> loadOmimGeneAssociations(String path) throws IOException {
		LinkedHashMap<String, LinkedHashSet<String>> associations = new LinkedHashMap<String, LinkedHashSet<String>>();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				try {
					String[] split = line.split("\t");
					if (split.length > 2 && split[2].equals("phenotype") && !split[1].equals("-")) {
						addAssociation(associations, split[0], split[1], "MedGen");
					}
				}
				catch (Exception e) {
					continue;
				}
			}
		}

		return associations;
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> loadOrphanetGeneAssociations(String ncbiGenePath, String orphanetXmlPath)
			throws IOException, ParserConfigurationException, SAXException {
		LinkedHashMap<String, String> ncbiGeneSymbolMap = loadNcbiGeneSymbolMap(ncbiGenePath);
		LinkedHashMap<String, LinkedHashSet<String>> associations = new LinkedHashMap<String, LinkedHashSet<String>>();

		DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
		DocumentBuilder documentBuilder = factory.newDocumentBuilder();
		Document document = documentBuilder.parse(orphanetXmlPath);
		Element root = document.getDocumentElement();
		NodeList disorderLists = root.getElementsByTagName("DisorderList");

		for (int i = 0; i < disorderLists.getLength(); i++) {
			Element disorderListElement = (Element) disorderLists.item(i);
			NodeList disorders = disorderListElement.getElementsByTagName("Disorder");

			for (int j = 0; j < disorders.getLength(); j++) {
				Element disorderElement = (Element) disorders.item(j);
				Element orphaNumberElement = (Element) disorderElement.getElementsByTagName("OrphaCode").item(0);
				NodeList symbols = disorderElement.getElementsByTagName("Symbol");

				for (int k = 0; k < symbols.getLength(); k++) {
					Element symbolElement = (Element) symbols.item(k);
					String ncbiId = ncbiGeneSymbolMap.get(symbolElement.getTextContent());
					if (ncbiId != null) {
						addAssociation(associations, orphaNumberElement.getTextContent(), ncbiId, "Orphanet");
					}
				}
			}
		}

		return associations;
	}

	// -----------------------------------------------------------------------------
	// -----------------------------------------------------------------------------

	public static GenCCAssociations loadGenccDefinitiveAssociations() throws IOException {
		LinkedHashSet<String> allowedClassificationCuries = new LinkedHashSet<String>();
		allowedClassificationCuries.add("GENCC:100001");
		return loadGenccAssociations(allowedClassificationCuries, true);
	}

	public static GenCCAssociations loadGenccAllAssociations() throws IOException {
		return loadGenccAssociations(null, true);
	}

	public static GenCCAssociations loadGenccCountCompatibleAssociations() throws IOException {
		LinkedHashSet<String> allowedClassificationCuries = new LinkedHashSet<String>();
		allowedClassificationCuries.add("GENCC:100001"); // Definitive
		allowedClassificationCuries.add("GENCC:100002"); // Strong
		allowedClassificationCuries.add("GENCC:100003"); // Moderate
		allowedClassificationCuries.add("GENCC:100004"); // Limited
		allowedClassificationCuries.add("GENCC:100009"); // Supportive
		return loadGenccAssociations(allowedClassificationCuries, false);
	}

	private static GenCCAssociations loadGenccAssociations(LinkedHashSet<String> allowedClassificationCuries,
			boolean projectMondoToMappedDiseases) throws IOException {
		LinkedHashMap<String, String> hgncToNcbiMap = loadHgncToNcbiMap(NCBI_GENE_INFO_PATH);
		MondoMapping mondoMapping = loadConfiguredMondoMapping();
		GenCCAssociations associations = new GenCCAssociations();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(GENCC_SUBMISSIONS_PATH)) {
			String line = reader.readLine();
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t", -1);
				if (split.length <= 7) {
					continue;
				}

				String hgncId = normalizeCurieValue(split[1], "HGNC:");
				String diseaseCurie = normalizeValue(split[3]);
				String originalDiseaseCurie = normalizeValue(split[5]);
				String classificationCurie = normalizeValue(split[7]);

				if (allowedClassificationCuries != null && !allowedClassificationCuries.contains(classificationCurie)) {
					continue;
				}

				String ncbiId = hgncToNcbiMap.get(hgncId);
				if (ncbiId == null) {
					continue;
				}

				if (originalDiseaseCurie != null && !originalDiseaseCurie.isEmpty() && originalDiseaseCurie.contains(":")) {
					addOriginalDiseaseAssociation(associations, ncbiId, originalDiseaseCurie);
				}
				else if (diseaseCurie != null && diseaseCurie.startsWith("MONDO:")) {
					addAssociation(associations.mondoAssociations, normalizeCurieValue(diseaseCurie, "MONDO:"), ncbiId, "GenCC");
				}

				if (diseaseCurie != null && diseaseCurie.startsWith("MONDO:")) {
					String mondoId = normalizeCurieValue(diseaseCurie, "MONDO:");
					addAssociation(associations.mondoAssociations, mondoId, ncbiId, "GenCC");

					if (projectMondoToMappedDiseases) {
						projectGeneToMappedDiseases(associations.omimAssociations, mondoMapping.mondoToOmim, mondoId, ncbiId, "GenCC");
						projectGeneToMappedDiseases(associations.orphanetAssociations, mondoMapping.mondoToOrpha, mondoId, ncbiId, "GenCC");
					}
				}
			}
		}

		return associations;
	}

	private static void addOriginalDiseaseAssociation(GenCCAssociations associations, String ncbiId, String originalDiseaseCurie) {
		if (originalDiseaseCurie.startsWith("OMIM:")) {
			addAssociation(associations.omimAssociations, normalizeCurieValue(originalDiseaseCurie, "OMIM:"), ncbiId, "GenCC");
		}
		else if (originalDiseaseCurie.startsWith("Orphanet:")) {
			addAssociation(associations.orphanetAssociations, normalizeCurieValue(originalDiseaseCurie, "Orphanet:"), ncbiId, "GenCC");
		}
		else if (originalDiseaseCurie.startsWith("MONDO:")) {
			addAssociation(associations.mondoAssociations, normalizeCurieValue(originalDiseaseCurie, "MONDO:"), ncbiId, "GenCC");
		}
	}

	private static String extractHgncId(String dbXrefs) {
		if (dbXrefs == null || dbXrefs.isEmpty()) {
			return null;
		}

		String[] refs = dbXrefs.split("\\|");
		for (String ref : refs) {
			if (ref.startsWith("HGNC:HGNC:")) {
				return ref.substring("HGNC:HGNC:".length());
			}
			if (ref.startsWith("HGNC:")) {
				String value = ref.substring("HGNC:".length());
				return value.startsWith("HGNC:") ? value.substring("HGNC:".length()) : value;
			}
		}

		return null;
	}

	private static String normalizeCurieValue(String value, String prefix) {
		String normalized = normalizeValue(value);
		return normalized.startsWith(prefix) ? normalized.substring(prefix.length()) : normalized;
	}

	private static String normalizeValue(String value) {
		if (value == null) {
			return null;
		}
		String normalized = value.trim();
		if (normalized.startsWith("\"") && normalized.endsWith("\"") && normalized.length() >= 2) {
			normalized = normalized.substring(1, normalized.length() - 1);
		}
		return normalized;
	}

	private static String normalizeMoiCurie(String moiCurie) {
		if (moiCurie == null || moiCurie.isEmpty()) {
			return null;
		}
		return moiCurie.replace(":", "_");
	}

	private static String resolveGenccSubmitterLabel(String submitterId) {
		String label = GENCC_SUBMITTER_LABELS.get(submitterId);
		return label != null ? label : submitterId;
	}

	private static LinkedHashMap<String, String> createGenccSubmitterLabelMap() {
		LinkedHashMap<String, String> labels = new LinkedHashMap<String, String>();
		labels.put("GENCC:000101", "Ambry Genetics");
		labels.put("GENCC:000102", "ClinGen");
		labels.put("GENCC:000103", "DECIPHER");
		labels.put("GENCC:000104", "Genomics England PanelApp");
		labels.put("GENCC:000105", "Illumina");
		labels.put("GENCC:000106", "Invitae");
		labels.put("GENCC:000107", "Laboratory for Molecular Medicine");
		labels.put("GENCC:000108", "Myriad Women's Health");
		labels.put("GENCC:000109", "Online Mendelian Inheritance in Man (OMIM)");
		labels.put("GENCC:000110", "Orphanet");
		labels.put("GENCC:000111", "PanelApp Australia");
		labels.put("GENCC:000112", "TGMI G2P");
		labels.put("GENCC:000113", "Franklin by Genoox");
		labels.put("GENCC:000114", "King Faisal Specialist Hospital and Research Center");
		return labels;
	}

	private static String escapeTurtleLiteral(String value) {
		if (value == null) {
			return "";
		}
		return value.replace("\\", "\\\\").replace("\"", "\\\"");
	}

	private static String toDiseasePathSegment(String diseaseCurie) {
		if (diseaseCurie == null) {
			return null;
		}
		if (diseaseCurie.startsWith("Orphanet:")) {
			return "ORDO:" + normalizeCurieValue(diseaseCurie, "Orphanet:");
		}
		return diseaseCurie;
	}

	private static String toDiseaseResource(String diseaseCurie) {
		if (diseaseCurie == null) {
			return null;
		}
		if (diseaseCurie.startsWith("OMIM:")) {
			return "mim:" + normalizeCurieValue(diseaseCurie, "OMIM:");
		}
		if (diseaseCurie.startsWith("Orphanet:")) {
			return "ordo:Orphanet_" + normalizeCurieValue(diseaseCurie, "Orphanet:");
		}
		if (diseaseCurie.startsWith("MONDO:")) {
			return "obo:MONDO_" + normalizeCurieValue(diseaseCurie, "MONDO:");
		}
		return null;
	}

	// -----------------------------------------------------------------------------
	// -----------------------------------------------------------------------------

	public static MergeStats mergeAssociationsFromTsv(String path, LinkedHashMap<String, LinkedHashSet<String>> associations, int diseaseIndex, int geneIndex, String source) throws IOException {
		return mergeAssociationsFromTsv(path, associations, diseaseIndex, geneIndex, source, false);
	}

	public static MergeStats mergeAssociationsFromTsv(String path, LinkedHashMap<String, LinkedHashSet<String>> associations, int diseaseIndex, int geneIndex, String source, boolean skipFirstLine) throws IOException {
		MergeStats stats = new MergeStats();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			if (skipFirstLine) {
				reader.readLine();
			}

			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t");
				if (split.length > Math.max(diseaseIndex, geneIndex)) {
					if (addAssociation(associations, split[diseaseIndex], split[geneIndex], source)) {
						++stats.added;
					}
					else {
						++stats.overlap;
					}
				}
			}
		}

		return stats;
	}

	public static boolean addAssociation(LinkedHashMap<String, LinkedHashSet<String>> associations, String diseaseId, String geneId, String source) {
		String key = diseaseId + "\t" + geneId;
		LinkedHashSet<String> sources = associations.get(key);
		if (sources == null) {
			sources = new LinkedHashSet<String>();
			associations.put(key, sources);
		}

		return sources.add(source);
	}

	public static void addProjectedMondoAssociations(LinkedHashMap<String, LinkedHashSet<String>> mondoAssociations,
			LinkedHashMap<String, LinkedHashSet<String>> sourceAssociations,
			Map<String, LinkedHashSet<String>> mondoMapping) {
		for (Map.Entry<String, LinkedHashSet<String>> entry : sourceAssociations.entrySet()) {
			String[] split = entry.getKey().split("\t");
			String diseaseId = split[0];
			String ncbiId = split[1];
			LinkedHashSet<String> mondoIds = mondoMapping.get(diseaseId);

			if (mondoIds == null) {
				continue;
			}

			for (String mondoId : mondoIds) {
				for (String source : entry.getValue()) {
					addAssociation(mondoAssociations, mondoId, ncbiId, source);
				}
			}
		}
	}

	public static void mergeAssociationMaps(LinkedHashMap<String, LinkedHashSet<String>> target,
			LinkedHashMap<String, LinkedHashSet<String>> source) {
		for (Map.Entry<String, LinkedHashSet<String>> entry : source.entrySet()) {
			String[] split = entry.getKey().split("\t");
			for (String sourceName : entry.getValue()) {
				addAssociation(target, split[0], split[1], sourceName);
			}
		}
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> buildMondoGeneAssociations()
			throws IOException, ParserConfigurationException, SAXException {
		return buildMondoGeneAssociations(loadGenccDefinitiveAssociations());
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> buildApiCompatibleMondoGeneAssociations()
			throws IOException, ParserConfigurationException, SAXException {
		return buildMondoGeneAssociations(loadGenccCountCompatibleAssociations());
	}

	private static LinkedHashMap<String, LinkedHashSet<String>> buildMondoGeneAssociations(GenCCAssociations genccAssociations)
			throws IOException, ParserConfigurationException, SAXException {
		MondoMapping mondoMapping = loadConfiguredMondoMapping();

		LinkedHashMap<String, LinkedHashSet<String>> omimNcbiGeneMap =
				loadOmimGeneAssociations(MEDGEN_MIM2GENE_PATH);
		LinkedHashMap<String, LinkedHashSet<String>> orphanetNcbiGeneMap =
				loadOrphanetGeneAssociations(NCBI_GENE_INFO_PATH, ORPHANET_PRODUCT6_PATH);

		LinkedHashMap<String, LinkedHashSet<String>> mondoNcbiGeneMap =
				new LinkedHashMap<String, LinkedHashSet<String>>();
		addProjectedMondoAssociations(mondoNcbiGeneMap, omimNcbiGeneMap, mondoMapping.omimToMondo);
		addProjectedMondoAssociations(mondoNcbiGeneMap, orphanetNcbiGeneMap, mondoMapping.orphaToMondo);

		mergeAssociationMaps(mondoNcbiGeneMap, genccAssociations.mondoAssociations);

		return mondoNcbiGeneMap;
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> buildFinalOmimGeneAssociations() throws IOException {
		return buildOmimGeneAssociations(loadGenccDefinitiveAssociations());
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> buildApiCompatibleOmimGeneAssociations() throws IOException {
		return buildOmimGeneAssociations(loadGenccCountCompatibleAssociations());
	}

	private static LinkedHashMap<String, LinkedHashSet<String>> buildOmimGeneAssociations(GenCCAssociations genccAssociations) throws IOException {
		LinkedHashMap<String, LinkedHashSet<String>> omimNcbiGeneMap =
				loadOmimGeneAssociations(MEDGEN_MIM2GENE_PATH);
		mergeAssociationMaps(omimNcbiGeneMap, genccAssociations.omimAssociations);
		return omimNcbiGeneMap;
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> buildFinalOrphanetGeneAssociations()
			throws IOException, ParserConfigurationException, SAXException {
		return buildOrphanetGeneAssociations(loadGenccDefinitiveAssociations());
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> buildApiCompatibleOrphanetGeneAssociations()
			throws IOException, ParserConfigurationException, SAXException {
		return buildOrphanetGeneAssociations(loadGenccCountCompatibleAssociations());
	}

	private static LinkedHashMap<String, LinkedHashSet<String>> buildOrphanetGeneAssociations(GenCCAssociations genccAssociations)
			throws IOException, ParserConfigurationException, SAXException {
		LinkedHashMap<String, LinkedHashSet<String>> orphanetNcbiGeneMap =
				loadOrphanetGeneAssociations(NCBI_GENE_INFO_PATH, ORPHANET_PRODUCT6_PATH);
		mergeAssociationMaps(orphanetNcbiGeneMap, genccAssociations.orphanetAssociations);
		return orphanetNcbiGeneMap;
	}

	public static void projectGeneToMappedDiseases(LinkedHashMap<String, LinkedHashSet<String>> targetAssociations,
			Map<String, LinkedHashSet<String>> mondoMapping,
			String mondoId,
			String ncbiId,
			String source) {
		LinkedHashSet<String> mappedIds = mondoMapping.get(mondoId);
		if (mappedIds == null) {
			return;
		}

		for (String mappedId : mappedIds) {
			addAssociation(targetAssociations, mappedId, ncbiId, source);
		}
	}

	private static void addToMapping(LinkedHashMap<String, LinkedHashSet<String>> map, String key, String value) {
		LinkedHashSet<String> values = map.get(key);
		if (values == null) {
			values = new LinkedHashSet<String>();
			map.put(key, values);
		}
		values.add(value);
	}

	public static MondoHierarchy loadMondoHierarchyFromOwl(String mondoOwlPath) throws IOException {
		MondoHierarchy hierarchy = new MondoHierarchy();
		String currentMondoId = null;
		boolean currentIsDeprecated = false;
		int currentClassDepth = 0;

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(mondoOwlPath)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String trimmed = line.trim();

				if (currentMondoId != null) {
					if (trimmed.equals("<owl:deprecated rdf:datatype=\"http://www.w3.org/2001/XMLSchema#boolean\">true</owl:deprecated>")) {
						currentIsDeprecated = true;
					}
					else if (!currentIsDeprecated && trimmed.startsWith("<rdfs:subClassOf rdf:resource=\"http://purl.obolibrary.org/obo/MONDO_")) {
						String parentMondoId = extractMondoIdFromUriLine(trimmed);
						if (parentMondoId != null) {
							addToMapping(hierarchy.parentToChildren, parentMondoId, currentMondoId);
						}
					}

					currentClassDepth += countOccurrences(trimmed, "<owl:Class");
					currentClassDepth -= countOccurrences(trimmed, "</owl:Class>");
					if (currentClassDepth <= 0) {
						currentMondoId = null;
						currentIsDeprecated = false;
						currentClassDepth = 0;
					}
					continue;
				}

				if (!trimmed.startsWith("<owl:Class rdf:about=\"http://purl.obolibrary.org/obo/MONDO_")) {
					continue;
				}

				currentMondoId = extractMondoIdFromUriLine(trimmed);
				currentIsDeprecated = false;
				currentClassDepth = 1;
				if (currentMondoId != null) {
					ensureMappingSet(hierarchy.parentToChildren, currentMondoId);
				}
			}
		}

		return hierarchy;
	}

	public static MondoExactMatchMapping loadMondoExactMatchMappingFromOwl(String mondoOwlPath) throws IOException {
		MondoExactMatchMapping mapping = new MondoExactMatchMapping();
		String currentMondoId = null;
		boolean currentIsDeprecated = false;
		int currentClassDepth = 0;

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(mondoOwlPath)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String trimmed = line.trim();

				if (currentMondoId != null) {
					if (trimmed.equals("<owl:deprecated rdf:datatype=\"http://www.w3.org/2001/XMLSchema#boolean\">true</owl:deprecated>")) {
						currentIsDeprecated = true;
					}
					else if (!currentIsDeprecated && trimmed.startsWith("<skos:exactMatch rdf:resource=\"")) {
						String exactMatchUri = extractUriValue(trimmed);
						if (exactMatchUri != null) {
							String omimId = extractOmimId(exactMatchUri);
							if (omimId != null) {
								addToMapping(mapping.mondoToOmim, currentMondoId, omimId);
							}

							String orphaId = extractOrphanetId(exactMatchUri);
							if (orphaId != null) {
								addToMapping(mapping.mondoToOrpha, currentMondoId, orphaId);
							}
						}
					}

					currentClassDepth += countOccurrences(trimmed, "<owl:Class");
					currentClassDepth -= countOccurrences(trimmed, "</owl:Class>");
					if (currentClassDepth <= 0) {
						currentMondoId = null;
						currentIsDeprecated = false;
						currentClassDepth = 0;
					}
					continue;
				}

				if (!trimmed.startsWith("<owl:Class rdf:about=\"http://purl.obolibrary.org/obo/MONDO_")) {
					continue;
				}

				currentMondoId = extractMondoIdFromUriLine(trimmed);
				currentIsDeprecated = false;
				currentClassDepth = 1;
			}
		}

		return mapping;
	}

	public static MondoMapping loadMondoMappingFromOwl(String mondoOwlPath) throws IOException {
		MondoMapping mapping = new MondoMapping();
		String currentMondoId = null;
		boolean currentIsDeprecated = false;
		int currentClassDepth = 0;

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(mondoOwlPath)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String trimmed = line.trim();

				if (currentMondoId != null) {
					if (trimmed.equals("<owl:deprecated rdf:datatype=\"http://www.w3.org/2001/XMLSchema#boolean\">true</owl:deprecated>")) {
						currentIsDeprecated = true;
					}
					else if (!currentIsDeprecated && trimmed.startsWith("<skos:exactMatch rdf:resource=\"")) {
						String exactMatchUri = extractUriValue(trimmed);
						if (exactMatchUri != null) {
							String omimId = extractOmimId(exactMatchUri);
							if (omimId != null) {
								addToMapping(mapping.mondoToOmim, currentMondoId, omimId);
								addToMapping(mapping.omimToMondo, omimId, currentMondoId);
							}

							String orphaId = extractOrphanetId(exactMatchUri);
							if (orphaId != null) {
								addToMapping(mapping.mondoToOrpha, currentMondoId, orphaId);
								addToMapping(mapping.orphaToMondo, orphaId, currentMondoId);
							}
						}
					}

					currentClassDepth += countOccurrences(trimmed, "<owl:Class");
					currentClassDepth -= countOccurrences(trimmed, "</owl:Class>");
					if (currentClassDepth <= 0) {
						currentMondoId = null;
						currentIsDeprecated = false;
						currentClassDepth = 0;
					}
					continue;
				}

				if (!trimmed.startsWith("<owl:Class rdf:about=\"http://purl.obolibrary.org/obo/MONDO_")) {
					continue;
				}

				currentMondoId = extractMondoIdFromUriLine(trimmed);
				currentIsDeprecated = false;
				currentClassDepth = 1;
			}
		}

		return mapping;
	}

	public static MondoHierarchy loadConfiguredMondoHierarchy() throws IOException {
		return loadMondoHierarchyFromOwl(MONDO_OWL_PATH);
	}

	public static MondoMapping loadConfiguredMondoMapping() throws IOException {
		return loadMondoMappingFromOwl(MONDO_OWL_PATH);
	}

	public static MondoExactMatchMapping loadConfiguredMondoExactMatchMapping() throws IOException {
		return loadMondoExactMatchMappingFromOwl(MONDO_OWL_PATH);
	}

	private static LinkedHashSet<String> ensureMappingSet(LinkedHashMap<String, LinkedHashSet<String>> map, String key) {
		LinkedHashSet<String> values = map.get(key);
		if (values == null) {
			values = new LinkedHashSet<String>();
			map.put(key, values);
		}
		return values;
	}

	private static String extractMondoIdFromUriLine(String line) {
		String marker = "http://purl.obolibrary.org/obo/MONDO_";
		int start = line.indexOf(marker);
		if (start < 0) {
			return null;
		}

		int valueStart = start + marker.length();
		int valueEnd = valueStart;
		while (valueEnd < line.length() && Character.isDigit(line.charAt(valueEnd))) {
			++valueEnd;
		}

		return valueEnd > valueStart ? line.substring(valueStart, valueEnd) : null;
	}

	private static String extractUriValue(String line) {
		String prefix = "rdf:resource=\"";
		int start = line.indexOf(prefix);
		if (start < 0) {
			return null;
		}

		int valueStart = start + prefix.length();
		int valueEnd = line.indexOf('"', valueStart);
		return valueEnd > valueStart ? line.substring(valueStart, valueEnd) : null;
	}

	private static int countOccurrences(String text, String token) {
		int count = 0;
		int index = 0;
		while ((index = text.indexOf(token, index)) >= 0) {
			++count;
			index += token.length();
		}
		return count;
	}

	private static String extractOmimId(String uri) {
		String[] markers = {"/omim/", "omim.org/entry/"};
		for (String marker : markers) {
			int start = uri.indexOf(marker);
			if (start >= 0) {
				start += marker.length();
				int end = start;
				while (end < uri.length() && Character.isDigit(uri.charAt(end))) {
					++end;
				}
				if (end > start) {
					return uri.substring(start, end);
				}
			}
		}
		return null;
	}

	private static String extractOrphanetId(String uri) {
		String marker = "Orphanet_";
		int start = uri.indexOf(marker);
		if (start < 0) {
			return null;
		}

		start += marker.length();
		int end = start;
		while (end < uri.length() && Character.isDigit(uri.charAt(end))) {
			++end;
		}
		return end > start ? uri.substring(start, end) : null;
	}

	// -----------------------------------------------------------------------------
	// -----------------------------------------------------------------------------

	public static void writeGeneAssociationTtl(String outputPath,
			LinkedHashMap<String, LinkedHashSet<String>> associations,
			String diseaseNamespaceInPath,
			String diseaseResourcePrefix,
			String diseasePrefixLine,
			LinkedHashMap<String, String> sourceUriMap) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX ncbigene: <http://identifiers.org/ncbigene/>"); writer.newLine();
			writer.write(diseasePrefixLine); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();
			writer.write("PREFIX sio: <http://semanticscience.org/resource/>"); writer.newLine();

			for (Map.Entry<String, LinkedHashSet<String>> entry : associations.entrySet()) {
				String[] split = entry.getKey().split("\t");
				String diseaseId = split[0];
				String ncbiId = split[1];

				writer.write("<https://pubcasefinder.dbcls.jp/gene_context/disease:" + diseaseNamespaceInPath + ":" + diseaseId + "/gene:ENT:" + ncbiId + ">");
				writer.newLine();
				writer.write("    a sio:SIO_000983 ;");
				writer.newLine();
				writer.write("    sio:SIO_000628 " + diseaseResourcePrefix + diseaseId + ", ncbigene:" + ncbiId + " ;");
				writer.newLine();
				writer.write("    dcterms:source ");

				int index = 0;
				int size = entry.getValue().size();
				for (String source : entry.getValue()) {
					String sourceUri = sourceUriMap.get(source);
					if (sourceUri == null) {
						continue;
					}

					++index;
					if (index == size) {
						writer.write("<" + sourceUri + "> .");
						writer.newLine();
					}
					else {
						writer.write("<" + sourceUri + ">, ");
					}
				}
			}
		}
	}

	public static void writeGenccGeneAssociationTtl(String outputPath, List<GenCCSubmissionRecord> records) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX gencc: <https://search.thegencc.org/submissions/>"); writer.newLine();
			writer.write("PREFIX nando: <http://nanbyodata.jp/ontology/nando#>"); writer.newLine();
			writer.write("PREFIX ncbigene: <http://identifiers.org/ncbigene/>"); writer.newLine();
			writer.write("PREFIX mim: <https://omim.org/entry/>"); writer.newLine();
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX ordo: <http://www.orpha.net/ORDO/>"); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();
			writer.write("PREFIX sio: <http://semanticscience.org/resource/>"); writer.newLine();

			for (GenCCSubmissionRecord record : records) {
				String diseasePath = toDiseasePathSegment(record.diseaseCurie);
				String diseaseResource = toDiseaseResource(record.diseaseCurie);
				if (diseasePath == null || diseaseResource == null || record.ncbiGeneId == null || record.genccId == null) {
					continue;
				}

				writer.write("<https://pubcasefinder.dbcls.jp/gene_context/disease:" + diseasePath + "/gene:ENT:" + record.ncbiGeneId + ">");
				writer.newLine();
				writer.write("    a sio:SIO_000983 ;");
				writer.newLine();
				writer.write("    sio:SIO_000628 " + diseaseResource + ", ncbigene:" + record.ncbiGeneId + " ;");
				writer.newLine();
				writer.write("    dcterms:source gencc:" + record.genccId + " .");
				writer.newLine();
				writer.write("gencc:" + record.genccId);
				writer.newLine();
				writer.write("    obo:IAO_0000114 \"" + escapeTurtleLiteral(record.classificationTitle) + "\" ;");
				writer.newLine();
				if (record.moiCurie != null && !record.moiCurie.isEmpty()) {
					writer.write("    nando:hasInheritance obo:" + record.moiCurie + " ;");
					writer.newLine();
				}
				writer.write("    dcterms:creator \"" + escapeTurtleLiteral(record.submitterLabel) + "\" .");
				writer.newLine();
			}
		}
	}
}
