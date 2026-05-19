package pubcasefinder_260415;

import java.io.BufferedWriter;
import java.io.IOException;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.TreeSet;

public class Mondo_Gene_Count {
	enum CountMode {
		API_COMPATIBLE,
		EXPANDED
	}

	public static void main(String[] args) throws Exception {
		LinkedHashMap<String, LinkedHashSet<String>> mondoGeneAssociations =
				DiseaseGeneAssociationUtil.buildApiCompatibleMondoGeneAssociations();
		LinkedHashMap<String, LinkedHashSet<String>> omimGeneAssociations =
				DiseaseGeneAssociationUtil.buildApiCompatibleOmimGeneAssociations();
		LinkedHashMap<String, LinkedHashSet<String>> orphanetGeneAssociations =
				DiseaseGeneAssociationUtil.buildApiCompatibleOrphanetGeneAssociations();
		DiseaseGeneAssociationUtil.MondoHierarchy mondoHierarchy =
				DiseaseGeneAssociationUtil.loadConfiguredMondoHierarchy();
		DiseaseGeneAssociationUtil.MondoExactMatchMapping exactMatchMapping =
				DiseaseGeneAssociationUtil.loadConfiguredMondoExactMatchMapping();
		CountMode countMode = resolveCountMode(args);
		LinkedHashMap<String, Integer> mondoGeneCountMap = buildMondoGeneCountMap(
				countMode,
				mondoHierarchy,
				mondoGeneAssociations,
				exactMatchMapping,
				omimGeneAssociations,
				orphanetGeneAssociations);

		System.out.println("Count Mode : " + countMode.name());
		System.out.println("MONDO_Gene_Association Count : " + mondoGeneAssociations.size());
		System.out.println("OMIM_Gene_Association Count : " + omimGeneAssociations.size());
		System.out.println("Orphanet_Gene_Association Count : " + orphanetGeneAssociations.size());
		System.out.println("MONDO_Gene_Count Count : " + mondoGeneCountMap.size());

		writeMondoGeneCountTtl(
				DiseaseGeneAssociationUtil.RDF_DIR + "/MONDO_Gene_Count.ttl",
				mondoGeneCountMap);
	}

	static LinkedHashMap<String, Integer> buildMondoGeneCountMap(
			CountMode countMode,
			DiseaseGeneAssociationUtil.MondoHierarchy mondoHierarchy,
			LinkedHashMap<String, LinkedHashSet<String>> mondoGeneAssociations,
			DiseaseGeneAssociationUtil.MondoExactMatchMapping exactMatchMapping,
			LinkedHashMap<String, LinkedHashSet<String>> omimGeneAssociations,
			LinkedHashMap<String, LinkedHashSet<String>> orphanetGeneAssociations) {
		LinkedHashMap<String, Integer> mondoGeneCountMap = new LinkedHashMap<String, Integer>();
		LinkedHashMap<String, LinkedHashSet<String>> directGeneMap =
				buildDirectGeneMap(mondoGeneAssociations);
		LinkedHashMap<String, LinkedHashSet<String>> omimGeneMap =
				buildDirectGeneMap(omimGeneAssociations);
		LinkedHashMap<String, LinkedHashSet<String>> orphanetGeneMap =
				buildDirectGeneMap(orphanetGeneAssociations);
		LinkedHashMap<String, LinkedHashSet<String>> subtreeGeneCache =
				new LinkedHashMap<String, LinkedHashSet<String>>();
		TreeSet<String> mondoIds = new TreeSet<String>();
		mondoIds.addAll(mondoHierarchy.parentToChildren.keySet());
		mondoIds.addAll(directGeneMap.keySet());
		mondoIds.addAll(exactMatchMapping.mondoToOmim.keySet());
		mondoIds.addAll(exactMatchMapping.mondoToOrpha.keySet());

		for (String mondoId : mondoIds) {
			LinkedHashSet<String> genes = collectGenesForMondoSubtree(
					countMode,
					mondoId,
					mondoHierarchy.parentToChildren,
					directGeneMap,
					exactMatchMapping,
					omimGeneMap,
					orphanetGeneMap,
					subtreeGeneCache,
					new LinkedHashSet<String>());
			if (!genes.isEmpty()) {
				mondoGeneCountMap.put(mondoId, genes.size());
			}
		}

		return mondoGeneCountMap;
	}

	private static CountMode resolveCountMode(String[] args) {
		if (args == null || args.length == 0) {
			return CountMode.API_COMPATIBLE;
		}

		String option = args[0].trim().toLowerCase();
		if ("expanded".equals(option) || "--expanded".equals(option)) {
			return CountMode.EXPANDED;
		}
		if ("api".equals(option) || "api-compatible".equals(option) || "--api-compatible".equals(option)) {
			return CountMode.API_COMPATIBLE;
		}

		throw new IllegalArgumentException("Unsupported count mode: " + args[0]);
	}

	private static LinkedHashMap<String, LinkedHashSet<String>> buildDirectGeneMap(
			LinkedHashMap<String, LinkedHashSet<String>> mondoGeneAssociations) {
		LinkedHashMap<String, LinkedHashSet<String>> directGeneMap =
				new LinkedHashMap<String, LinkedHashSet<String>>();
		for (String associationKey : mondoGeneAssociations.keySet()) {
			String[] split = associationKey.split("\t", -1);
			if (split.length < 2 || split[0].isEmpty() || split[1].isEmpty()) {
				continue;
			}
			LinkedHashSet<String> genes = directGeneMap.get(split[0]);
			if (genes == null) {
				genes = new LinkedHashSet<String>();
				directGeneMap.put(split[0], genes);
			}
			genes.add(split[1]);
		}
		return directGeneMap;
	}

	private static LinkedHashSet<String> collectGenesForMondoSubtree(
			CountMode countMode,
			String mondoId,
			LinkedHashMap<String, LinkedHashSet<String>> parentToChildren,
			LinkedHashMap<String, LinkedHashSet<String>> directGeneMap,
			DiseaseGeneAssociationUtil.MondoExactMatchMapping exactMatchMapping,
			LinkedHashMap<String, LinkedHashSet<String>> omimGeneMap,
			LinkedHashMap<String, LinkedHashSet<String>> orphanetGeneMap,
			LinkedHashMap<String, LinkedHashSet<String>> subtreeGeneCache,
			LinkedHashSet<String> visiting) {
		LinkedHashSet<String> cachedGenes = subtreeGeneCache.get(mondoId);
		if (cachedGenes != null) {
			return cachedGenes;
		}
		if (!visiting.add(mondoId)) {
			return new LinkedHashSet<String>();
		}

		LinkedHashSet<String> genes = new LinkedHashSet<String>();
		if (countMode == CountMode.EXPANDED) {
			addDirectMondoGenes(genes, mondoId, directGeneMap);
		}
		addExactMatchedDiseaseGenes(genes, mondoId, exactMatchMapping.mondoToOmim, omimGeneMap);
		addExactMatchedDiseaseGenes(genes, mondoId, exactMatchMapping.mondoToOrpha, orphanetGeneMap);

		LinkedHashSet<String> children = parentToChildren.get(mondoId);
		if (children != null) {
			for (String childMondoId : children) {
				genes.addAll(collectGenesForMondoSubtree(
						countMode,
						childMondoId,
						parentToChildren,
						directGeneMap,
						exactMatchMapping,
						omimGeneMap,
						orphanetGeneMap,
						subtreeGeneCache,
						visiting));
			}
		}

		visiting.remove(mondoId);
		subtreeGeneCache.put(mondoId, genes);
		return genes;
	}

	private static void addDirectMondoGenes(
			LinkedHashSet<String> genes,
			String mondoId,
			LinkedHashMap<String, LinkedHashSet<String>> directGeneMap) {
		LinkedHashSet<String> directGenes = directGeneMap.get(mondoId);
		if (directGenes != null) {
			genes.addAll(directGenes);
		}
	}

	private static void addExactMatchedDiseaseGenes(
			LinkedHashSet<String> genes,
			String mondoId,
			LinkedHashMap<String, LinkedHashSet<String>> mondoToDiseaseIds,
			LinkedHashMap<String, LinkedHashSet<String>> diseaseGeneMap) {
		LinkedHashSet<String> diseaseIds = mondoToDiseaseIds.get(mondoId);
		if (diseaseIds == null) {
			return;
		}
		for (String diseaseId : diseaseIds) {
			LinkedHashSet<String> matchedGenes = diseaseGeneMap.get(diseaseId);
			if (matchedGenes != null) {
				genes.addAll(matchedGenes);
			}
		}
	}

	static void writeMondoGeneCountTtl(String outputPath, LinkedHashMap<String, Integer> mondoGeneCountMap) throws IOException {
		try (BufferedWriter writer = RdfBuildSupport.createBufferedWriter(outputPath)) {
			writer.write("PREFIX obo: <http://purl.obolibrary.org/obo/>"); writer.newLine();
			writer.write("PREFIX sio: <http://semanticscience.org/resource/>"); writer.newLine();
			writer.write("PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>"); writer.newLine();

			for (Map.Entry<String, Integer> entry : mondoGeneCountMap.entrySet()) {
				writer.write("obo:MONDO_" + entry.getKey()
						+ " sio:SIO_001112 \"" + entry.getValue() + "\"^^xsd:integer .");
				writer.newLine();
			}
		}
	}
}
