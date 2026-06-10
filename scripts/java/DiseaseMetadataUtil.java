package pubcasefinder_260415;

import java.io.BufferedReader;
import java.io.BufferedWriter;
import java.io.FileReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Properties;

// OMIM/Orphanet 질환 메타데이터 생성에 필요한 공통 로직을 모은 유틸리티
public class DiseaseMetadataUtil {
	public static final String CONFIG_PATH = RdfBuildSupport.CONFIG_PATH;
	private static final Properties CONFIG = RdfBuildSupport.loadConfig();

	public static final String OMIM_MIM2GENE_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "omim.mim2gene.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "omim.dir"), "mim2gene.txt");
	public static final String MEDGEN_OMIM_HPO_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "medgen.omim.hpo.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "medgen.dir"), "MedGen_HPO_OMIM_Mapping.txt.gz");
	public static final String MONDO_OWL_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "mondo.owl.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "mondo.dir"), "mondo-international.owl");
	public static final String KEGG_DISEASE_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "kegg.disease.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "kegg.dir"), "KEGG_disease.tsv");
	public static final String GENE_REVIEWS_PATH = RdfBuildSupport.resolveConfiguredFile(CONFIG, "genereviews.omim.path", RdfBuildSupport.resolveResourceRoot(CONFIG, "genereviews.dir"), "NBKid_shortname_OMIM.txt");
	public static final String RDF_DIR = RdfBuildSupport.resolveConfiguredOutputDir(CONFIG);

	public static class DiseaseMappings {
		LinkedHashMap<String, LinkedHashSet<String>> omimToMondo = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, LinkedHashSet<String>> omimToUmls = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashMap<String, String> orphanetToMondo = new LinkedHashMap<String, String>();
		LinkedHashMap<String, String> orphanetToOmim = new LinkedHashMap<String, String>();
		LinkedHashMap<String, LinkedHashSet<String>> orphanetToUmls = new LinkedHashMap<String, LinkedHashSet<String>>();
		LinkedHashSet<String> orphanetIds = new LinkedHashSet<String>();
	}

	public static class SharedReferenceData {
		LinkedHashMap<String, LinkedHashSet<String>> inheritanceMap;
		DiseaseMappings mappings;
		LinkedHashMap<String, String> keggMap;
		LinkedHashMap<String, LinkedHashSet<String>> geneReviewsMap;
	}

	private static void addValue(LinkedHashMap<String, LinkedHashSet<String>> map, String key, String value) {
		LinkedHashSet<String> values = map.get(key);
		if (values == null) {
			values = new LinkedHashSet<String>();
			map.put(key, values);
		}
		values.add(value);
	}

	public static LinkedHashSet<String> loadOmimDiseaseIds(String path) throws IOException {
		LinkedHashSet<String> omimIds = new LinkedHashSet<String>();
		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			for (int i = 0; i < 4; i++) {
				reader.readLine();
			}
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t");
				if (split.length <= 1) {
					continue;
				}
				String type = split[1];
				if (" ".equals(type) || "phenotype".equals(type) || "predominantly phenotypes".equals(type)) {
					omimIds.add(split[0]);
				}
			}
		}
		return omimIds;
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> loadOmimInheritanceMap(String path) throws IOException {
		LinkedHashMap<String, LinkedHashSet<String>> inheritanceMap = new LinkedHashMap<String, LinkedHashSet<String>>();
		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			reader.readLine();
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\\|");
				if (split.length <= 5) {
					continue;
				}
				if ("inheritance_type_of".equals(split[3])) {
					addValue(inheritanceMap, split[1], split[5].replace("HP:", ""));
				}
			}
		}
		return inheritanceMap;
	}

	public static DiseaseMappings loadDiseaseMappingsFromOwl(String mondoOwlPath) throws IOException {
		DiseaseMappings mappings = new DiseaseMappings();
		String currentMondoId = null;
		boolean currentIsDeprecated = false;
		int currentClassDepth = 0;
		LinkedHashSet<String> omimIds = new LinkedHashSet<String>();
		LinkedHashSet<String> orphanetIds = new LinkedHashSet<String>();
		LinkedHashSet<String> umlsIds = new LinkedHashSet<String>();

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
							String omimId = extractIdFromUri(exactMatchUri, "/entry/");
							if (omimId != null && isAllDigits(omimId)) {
								omimIds.add(omimId);
							}

							String orphanetId = extractIdFromUri(exactMatchUri, "Orphanet_");
							if (orphanetId != null && isAllDigits(orphanetId)) {
								orphanetIds.add(orphanetId);
							}

							String umlsId = extractIdFromUri(exactMatchUri, "/id/C");
							if (umlsId != null && isAllDigits(umlsId)) {
								umlsIds.add("C" + umlsId);
							}

						}
					}

					currentClassDepth += countOccurrences(trimmed, "<owl:Class");
					currentClassDepth -= countOccurrences(trimmed, "</owl:Class>");
					if (currentClassDepth <= 0) {
						finalizeMondoTerm(mappings, currentMondoId, omimIds, orphanetIds, umlsIds, currentIsDeprecated);
						currentMondoId = null;
						currentIsDeprecated = false;
						currentClassDepth = 0;
						omimIds.clear();
						orphanetIds.clear();
						umlsIds.clear();
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

		return mappings;
	}

	public static DiseaseMappings loadConfiguredDiseaseMappings() throws IOException {
		return loadDiseaseMappingsFromOwl(MONDO_OWL_PATH);
	}

	/** OMIM/Orphanet 메타데이터 생성에 공통으로 쓰는 참조 데이터를 한 번에 적재한다. */
	public static SharedReferenceData loadSharedReferenceData() throws IOException {
		SharedReferenceData data = new SharedReferenceData();
		data.inheritanceMap = loadOmimInheritanceMap(MEDGEN_OMIM_HPO_PATH);
		data.mappings = loadConfiguredDiseaseMappings();
		data.keggMap = loadKeggMap(KEGG_DISEASE_PATH);
		data.geneReviewsMap = loadGeneReviewsMap(GENE_REVIEWS_PATH);
		return data;
	}

	private static void finalizeMondoTerm(
			DiseaseMappings mappings,
			String mondoId,
			LinkedHashSet<String> omimIds,
			LinkedHashSet<String> orphanetIds,
			LinkedHashSet<String> umlsIds,
			boolean obsolete) {
		if (obsolete || mondoId == null) {
			return;
		}
		for (String omimId : omimIds) {
			addValue(mappings.omimToMondo, omimId, mondoId);
			for (String umlsId : umlsIds) {
				addValue(mappings.omimToUmls, omimId, umlsId);
			}
		}
		for (String orphanetId : orphanetIds) {
			mappings.orphanetIds.add(orphanetId);
			if (!mappings.orphanetToMondo.containsKey(orphanetId)) {
				mappings.orphanetToMondo.put(orphanetId, mondoId);
			}
			if (omimIds.size() == 1 && !mappings.orphanetToOmim.containsKey(orphanetId)) {
				mappings.orphanetToOmim.put(orphanetId, omimIds.iterator().next());
			}
			for (String umlsId : umlsIds) {
				addValue(mappings.orphanetToUmls, orphanetId, umlsId);
			}
		}
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

	private static String extractIdFromUri(String uri, String marker) {
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

	private static boolean isAllDigits(String value) {
		if (value == null || value.isEmpty()) {
			return false;
		}
		for (int i = 0; i < value.length(); ++i) {
			if (!Character.isDigit(value.charAt(i))) {
				return false;
			}
		}
		return true;
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

	public static LinkedHashMap<String, String> loadKeggMap(String path) throws IOException {
		LinkedHashMap<String, String> keggMap = new LinkedHashMap<String, String>();
		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t");
				if (split.length > 1 && !keggMap.containsKey(split[0])) {
					keggMap.put(split[0], split[1]);
				}
			}
		}
		return keggMap;
	}

	public static LinkedHashMap<String, LinkedHashSet<String>> loadGeneReviewsMap(String path) throws IOException {
		LinkedHashMap<String, LinkedHashSet<String>> geneReviewsMap = new LinkedHashMap<String, LinkedHashSet<String>>();
		try (BufferedReader reader = RdfBuildSupport.openUtf8Reader(path)) {
			reader.readLine();
			String line;
			while ((line = reader.readLine()) != null) {
				String[] split = line.split("\t");
				if (split.length > 2) {
					addValue(geneReviewsMap, split[2], split[0]);
				}
			}
		}
		return geneReviewsMap;
	}

	private static void writeValues(BufferedWriter writer, String prefix, LinkedHashSet<String> values) throws IOException {
		writeValues(writer, prefix, "", values);
	}

	private static void writeValues(BufferedWriter writer, String prefix, String suffix, LinkedHashSet<String> values) throws IOException {
		int index = 0;
		int size = values.size();
		for (String value : values) {
			index++;
			writer.write(prefix + value + suffix);
			if (index < size) {
				writer.write(", ");
			}
		}
	}

	public static void writeOmimDiseaseTtl(
			String outputPath,
			LinkedHashSet<String> omimIds,
			LinkedHashMap<String, LinkedHashSet<String>> inheritanceMap,
			DiseaseMappings mappings,
			LinkedHashMap<String, String> keggMap,
			LinkedHashMap<String, LinkedHashSet<String>> geneReviewsMap) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX genereviews: <https://www.ncbi.nlm.nih.gov/books/>"); writer.newLine();
			writer.write("PREFIX gtr: <https://www.ncbi.nlm.nih.gov/gtr/all/tests/?term=>"); writer.newLine();
			writer.write("PREFIX kegg: <http://www.kegg.jp/entry/>"); writer.newLine();
			writer.write("PREFIX nando: <http://nanbyodata.jp/ontology/nando#>"); writer.newLine();
			writer.write("PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>"); writer.newLine();
			writer.write("PREFIX med2rdf: <http://med2rdf.org/ontology/>"); writer.newLine();
			writer.write("PREFIX mim: <https://omim.org/entry/>"); writer.newLine();
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();

			for (String omimId : omimIds) {
				writer.write("mim:" + omimId); writer.newLine();
				writer.write("    a med2rdf:Disease, ncit:C7057 ;"); writer.newLine();
				writer.write("    dcterms:identifier \"" + omimId + "\"");

				if (inheritanceMap.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    nando:hasInheritance ");
					writeValues(writer, "obo:HP_", inheritanceMap.get(omimId));
				}
				if (mappings.omimToMondo.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso ");
					writeValues(writer, "obo:MONDO_", mappings.omimToMondo.get(omimId));
				}
				if (keggMap.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso kegg:" + keggMap.get(omimId));
				}
				if (geneReviewsMap.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso ");
					writeValues(writer, "genereviews:", geneReviewsMap.get(omimId));
				}
				if (mappings.omimToUmls.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso ");
					writeValues(writer, "gtr:", mappings.omimToUmls.get(omimId));
					writer.write(" .");
					writer.newLine();
				}
				else {
					writer.write(" .");
					writer.newLine();
				}
			}
		}
	}

	public static void writeOrphanetDiseaseTtl(
			String outputPath,
			DiseaseMappings mappings,
			LinkedHashMap<String, LinkedHashSet<String>> inheritanceMap,
			LinkedHashMap<String, String> keggMap,
			LinkedHashMap<String, LinkedHashSet<String>> geneReviewsMap) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX dcterms: <http://purl.org/dc/terms/>"); writer.newLine();
			writer.write("PREFIX genereviews: <https://www.ncbi.nlm.nih.gov/books/>"); writer.newLine();
			writer.write("PREFIX gtr: <https://www.ncbi.nlm.nih.gov/gtr/all/tests/?term=>"); writer.newLine();
			writer.write("PREFIX kegg: <http://www.kegg.jp/entry/>"); writer.newLine();
			writer.write("PREFIX nando: <http://nanbyodata.jp/ontology/nando#>"); writer.newLine();
			writer.write("PREFIX ncit: <http://ncicb.nci.nih.gov/xml/owl/EVS/Thesaurus.owl#>"); writer.newLine();
			writer.write("PREFIX med2rdf: <http://med2rdf.org/ontology/>"); writer.newLine();
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX ordo: <http://www.orpha.net/ORDO/>"); writer.newLine();
			writer.write("PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>"); writer.newLine();
			writer.write("PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>"); writer.newLine();

			for (String orphanetId : mappings.orphanetIds) {
				String omimId = mappings.orphanetToOmim.get(orphanetId);
				writer.write("ordo:Orphanet_" + orphanetId); writer.newLine();
				writer.write("    a med2rdf:Disease, ncit:C7057 ;"); writer.newLine();
				writer.write("    dcterms:identifier \"" + orphanetId + "\"");

				if (omimId != null && inheritanceMap.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    nando:hasInheritance ");
					writeValues(writer, "obo:HP_", inheritanceMap.get(omimId));
				}
				if (mappings.orphanetToMondo.get(orphanetId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso obo:MONDO_" + mappings.orphanetToMondo.get(orphanetId));
				}
				if (omimId != null && keggMap.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso kegg:" + keggMap.get(omimId));
				}
				if (omimId != null && geneReviewsMap.get(omimId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso ");
					writeValues(writer, "genereviews:", geneReviewsMap.get(omimId));
				}
				if (mappings.orphanetToUmls.get(orphanetId) != null) {
					writer.write(" ;"); writer.newLine();
					writer.write("    rdfs:seeAlso ");
					writeValues(writer, "gtr:", mappings.orphanetToUmls.get(orphanetId));
					writer.write(" .");
					writer.newLine();
				}
				else {
					writer.write(" .");
					writer.newLine();
				}
			}
		}
	}
}
