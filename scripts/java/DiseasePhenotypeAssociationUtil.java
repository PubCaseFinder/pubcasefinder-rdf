package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Properties;

import javax.xml.parsers.DocumentBuilder;
import javax.xml.parsers.DocumentBuilderFactory;
import javax.xml.parsers.ParserConfigurationException;

import org.w3c.dom.Document;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import org.xml.sax.SAXException;

// 질환-표현형 연관 RDF 생성에 필요한 공통 로직을 모은 유틸리티
public class DiseasePhenotypeAssociationUtil {
	private static final Properties CONFIG = RdfBuildSupport.loadConfig();
	public static final String ORPHANET_PRODUCT4_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "orphanet.product4.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "orphanet.dir"), "en_product4.xml");
	public static final String HPO_PHENOTYPE_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "hpo.phenotype.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "hpo.dir"), "phenotype.hpoa");
	public static final String RDF_DIR = RdfBuildSupport.resolveConfiguredOutputDir(CONFIG);
	public static final String HPOA_SOURCE_URI = "http://compbio.charite.de/jenkins/job/hpo.annotations.current/lastSuccessfulBuild/artifact/current/phenotype.hpoa";

	private static final LinkedHashMap<String, String> ORDO_FREQUENCY_TO_HPO = createOrdoFrequencyMap();

	public static class AnnotationSource {
		String creator;
		String page;
	}

	private static class OrdoPhenotypeAnnotation {
		String ordoId;
		String hpoId;
		String frequencyTermId;
	}

	public static LinkedHashMap<String, String> loadOrdoFrequencyAnnotations(String orphanetProduct4Path)
			throws IOException, ParserConfigurationException, SAXException {
		LinkedHashMap<String, String> frequencies = new LinkedHashMap<String, String>();

		DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
		DocumentBuilder documentBuilder = factory.newDocumentBuilder();
		Document document = documentBuilder.parse(orphanetProduct4Path);
		Element root = document.getDocumentElement();
		NodeList disorderLists = root.getElementsByTagName("HPODisorderSetStatusList");

		for (int i = 0; i < disorderLists.getLength(); i++) {
			Element disorderList = (Element) disorderLists.item(i);
			NodeList disorders = disorderList.getElementsByTagName("Disorder");
			for (int j = 0; j < disorders.getLength(); j++) {
				Element disorder = (Element) disorders.item(j);
				Element orphaCode = (Element) disorder.getElementsByTagName("OrphaCode").item(0);
				if (orphaCode == null) {
					continue;
				}

				NodeList hpoIds = disorder.getElementsByTagName("HPOId");
				NodeList hpoFrequencies = disorder.getElementsByTagName("HPOFrequency");
				for (int k = 0; k < Math.min(hpoIds.getLength(), hpoFrequencies.getLength()); k++) {
					Element hpoIdElement = (Element) hpoIds.item(k);
					Element hpoFrequencyElement = (Element) hpoFrequencies.item(k);
					String frequencyLabel = extractFrequencyLabel(hpoFrequencyElement);
					if (frequencyLabel == null) {
						continue;
					}

					String key = orphaCode.getTextContent().trim() + "\t" + normalizeHpoId(hpoIdElement.getTextContent());
					if (!frequencies.containsKey(key)) {
						frequencies.put(key, frequencyLabel);
					}
				}
			}
		}

		return frequencies;
	}

	public static LinkedHashMap<String, String> loadManualPhenotypeAssociations(String phenotypeHpoaPath, String diseasePrefix) throws IOException {
		LinkedHashMap<String, String> manualAssociations = new LinkedHashMap<String, String>();

		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(phenotypeHpoaPath)) {
			String line;
			while ((line = reader.readLine()) != null) {
				if (line.startsWith("#")) {
					continue;
				}

				String[] split = line.split("\t");
				if (split.length <= 3 || !split[0].startsWith(diseasePrefix + ":")) {
					continue;
				}

				String diseaseId = split[0].substring((diseasePrefix + ":").length()).trim();
				String hpoId = normalizeHpoId(split[3]);
				String key = diseaseId + "\t" + hpoId;
				if (!manualAssociations.containsKey(key)) {
					manualAssociations.put(key, "Manual");
				}
			}
		}

		return manualAssociations;
	}

	private static String extractFrequencyLabel(Element hpoFrequencyElement) {
		if (hpoFrequencyElement == null) {
			return null;
		}
		NodeList names = hpoFrequencyElement.getElementsByTagName("Name");
		if (names.getLength() == 0) {
			return null;
		}
		return names.item(0).getTextContent().trim();
	}

	private static String normalizeHpoId(String value) {
		return value.trim().replace("HP:", "");
	}

	private static LinkedHashMap<String, String> createOrdoFrequencyMap() {
		LinkedHashMap<String, String> map = new LinkedHashMap<String, String>();
		map.put("Obligate (100%)", "0040280");
		map.put("Very frequent (99-80%)", "0040281");
		map.put("Frequent (79-30%)", "0040282");
		map.put("Occasional (29-5%)", "0040283");
		map.put("Very rare (<4-1%)", "0040284");
		map.put("Excluded (0%)", "0040285");
		return map;
	}

	/** annotation source blank node에 들어갈 작성자와 페이지 정보를 생성한다. */
	public static AnnotationSource createAnnotationSource(String creator, String page) {
		AnnotationSource source = new AnnotationSource();
		source.creator = creator;
		source.page = page;
		return source;
	}

	public static void writeOrdoPhenotypeAssociationTtl(
			String outputPath,
			Map<String, String> manualAssociations,
			Map<String, String> frequencyByAssociation,
			AnnotationSource source) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX foaf: <http://xmlns.com/foaf/0.1>"); writer.newLine();
			writer.write("PREFIX hoom: <http://www.semanticweb.org/ontology/HOOM#>"); writer.newLine();
			writer.write("PREFIX oa: <http://www.w3.org/ns/oa#>"); writer.newLine();
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX ordo: <http://www.orpha.net/ORDO/>"); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();

			int blankNodeCounter = 0;
			for (OrdoPhenotypeAnnotation annotation : buildOrdoAnnotations(manualAssociations, frequencyByAssociation)) {
				writer.write("<https://pubcasefinder.dbcls.jp/phenotype_context/disease:ORDO:" + annotation.ordoId + "/phenotype:HP:" + annotation.hpoId + ">");
				writer.newLine();
				writer.write("    a oa:Annotation ;");
				writer.newLine();
				writer.write("    oa:hasTarget ordo:Orphanet_" + annotation.ordoId + " ;");
				writer.newLine();
				writer.write("    oa:hasBody obo:HP_" + annotation.hpoId + " ;");
				writer.newLine();
				if (annotation.frequencyTermId != null) {
					writer.write("    hoom:with_frequency obo:HP_" + annotation.frequencyTermId + " ;");
					writer.newLine();
				}
				writer.write("    dcterms:source _:b" + (++blankNodeCounter) + " ;");
				writer.newLine();
				writer.write("    obo:ECO_9000001 obo:ECO_0000218 .");
				writer.newLine();

				writer.write("_:b" + blankNodeCounter);
				writer.newLine();
				writer.write("    dcterms:creator \"" + source.creator + "\" ;");
				writer.newLine();
				writer.write("    foaf:page <" + source.page + "> .");
				writer.newLine();
			}

			writeFrequencyLabels(writer);
		}
	}

	public static void writeManualPhenotypeAssociationTtl(
			String outputPath,
			String diseaseNamespaceInPath,
			String diseaseResourcePrefix,
			String diseasePrefixLine,
			Map<String, String> manualAssociations,
			AnnotationSource source) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX foaf: <http://xmlns.com/foaf/0.1>"); writer.newLine();
			writer.write(diseasePrefixLine); writer.newLine();
			writer.write("PREFIX oa: <http://www.w3.org/ns/oa#>"); writer.newLine();
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();

			int blankNodeCounter = 0;
			for (String key : manualAssociations.keySet()) {
				String[] split = key.split("\t");
				String diseaseId = split[0];
				String hpoId = split[1];

				writer.write("<https://pubcasefinder.dbcls.jp/phenotype_context/disease:" + diseaseNamespaceInPath + ":" + diseaseId + "/phenotype:HP:" + hpoId + ">");
				writer.newLine();
				writer.write("    a oa:Annotation ;");
				writer.newLine();
				writer.write("    oa:hasTarget " + diseaseResourcePrefix + diseaseId + " ;");
				writer.newLine();
				writer.write("    oa:hasBody obo:HP_" + hpoId + " ;");
				writer.newLine();
				writer.write("    dcterms:source _:b" + (++blankNodeCounter) + " ;");
				writer.newLine();
				writer.write("    obo:ECO_9000001 obo:ECO_0000218 .");
				writer.newLine();

				writer.write("_:b" + blankNodeCounter);
				writer.newLine();
				writer.write("    dcterms:creator \"" + source.creator + "\" ;");
				writer.newLine();
				writer.write("    foaf:page <" + source.page + "> .");
				writer.newLine();
			}
		}
	}

	private static Iterable<OrdoPhenotypeAnnotation> buildOrdoAnnotations(
			Map<String, String> manualAssociations,
			Map<String, String> frequencyByAssociation) {
		LinkedHashMap<String, OrdoPhenotypeAnnotation> annotations = new LinkedHashMap<String, OrdoPhenotypeAnnotation>();
		for (String key : manualAssociations.keySet()) {
			String[] split = key.split("\t");
			OrdoPhenotypeAnnotation annotation = new OrdoPhenotypeAnnotation();
			annotation.ordoId = split[0];
			annotation.hpoId = split[1];
			String frequencyLabel = frequencyByAssociation.get(key);
			annotation.frequencyTermId = ORDO_FREQUENCY_TO_HPO.get(frequencyLabel);
			annotations.put(key, annotation);
		}
		return annotations.values();
	}

	private static void writeFrequencyLabels(BufferedWriter writer) throws IOException {
		for (Map.Entry<String, String> entry : ORDO_FREQUENCY_TO_HPO.entrySet()) {
			writer.write("obo:HP_" + entry.getValue());
			writer.newLine();
			writer.write("    rdfs:label \"" + entry.getKey() + "\"@en .");
			writer.newLine();
		}
	}
}
