from package import hp_ja


def test_load_hpo_japanese_labels(tmp_path):
    inheritance_path = tmp_path / "HPO_Inheritance_en_jp.txt"
    inheritance_path.write_text(
        "\t".join(["HPO ID", "English", "日本語"]) + "\n"
        + "\t".join(["HP:0000006", "Autosomal dominant inheritance", "inheritance label"])
        + "\n",
        encoding="utf-8",
    )

    japanese_path = tmp_path / "HPO-japanese.alpha.21Jul2023.tsv"
    japanese_path.write_text(
        "\t".join(
            [
                "source",
                "source_version",
                "source_language",
                "translation_language",
                "subject_id",
                "predicate_id",
                "source_value",
                "translation_value",
                "translator",
                "translation_date",
                "translation_confidence",
                "translation_precision",
                "translation_type",
                "translation_status",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "hp.owl",
                "2023-07-21",
                "en",
                "ja",
                "HP:0000006",
                "rdfs:label",
                "Autosomal dominant inheritance",
                "official duplicate",
                "",
                "2023-07-31",
                "1",
                "EXACT",
                "",
                "OFFICIAL",
            ]
        )
        + "\n"
        + "\t".join(
            [
                "hp.owl",
                "2023-07-21",
                "en",
                "ja",
                "HP:0000002",
                "rdfs:label",
                "Abnormality of body height",
                "official label",
                "",
                "2023-07-31",
                "1",
                "EXACT",
                "",
                "OFFICIAL",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    labels, inheritance_count, official_count = hp_ja.load_hpo_japanese_labels(
        inheritance_path,
        japanese_path,
    )

    assert inheritance_count == 1
    assert official_count == 2
    assert labels == {
        "0000006": "inheritance label",
        "0000002": "official label",
    }


def test_add_inheritance_labels(tmp_path):
    inheritance_path = tmp_path / "HPO_Inheritance_en_jp.txt"
    
    inheritance_path.write_text(
        "\t".join(["HPO ID", "English", "日本語"]) + "\n"
        + "\t".join(["HP:0000006", "Autosomal dominant inheritance", "inheritance label"])
        + "\n"
        + "\t".join(["HP:0000007", "Autosomal recessive inheritance", ""])
        + "\n",
        encoding="utf-8",
    )
    labels = {}

    count = hp_ja.add_inheritance_labels(inheritance_path, labels)

    assert count == 1
    assert labels == {
        "0000006": "inheritance label",
    }


def test_add_official_japanese_labels(tmp_path):
    japanese_path = tmp_path / "HPO-japanese.alpha.21Jul2023.tsv"
    header = [
        "source",
        "source_version",
        "source_language",
        "translation_language",
        "subject_id",
        "predicate_id",
        "source_value",
        "translation_value",
        "translator",
        "translation_date",
        "translation_confidence",
        "translation_precision",
        "translation_type",
        "translation_status",
    ]
    official_row = [
        "hp.owl",
        "2023-07-21",
        "en",
        "ja",
        "HP:0000002",
        "rdfs:label",
        "Abnormality of body height",
        "official label",
        "",
        "2023-07-31",
        "1",
        "EXACT",
        "",
        "OFFICIAL",
    ]
    unofficial_row = [
        "hp.owl",
        "2023-07-21",
        "en",
        "ja",
        "HP:0000003",
        "rdfs:label",
        "Multicystic kidney dysplasia",
        "unofficial label",
        "",
        "2023-07-31",
        "1",
        "EXACT",
        "",
        "DRAFT",
    ]
    na_row = [
        "hp.owl",
        "2023-07-21",
        "en",
        "ja",
        "HP:0000004",
        "rdfs:label",
        "All",
        "NA",
        "",
        "2023-07-31",
        "1",
        "EXACT",
        "",
        "OFFICIAL",
    ]
    japanese_path.write_text(
        "\n".join(
            [
                "\t".join(header),
                "\t".join(official_row),
                "\t".join(unofficial_row),
                "\t".join(na_row),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    labels = {
        "0000002": "existing label",
    }

    count = hp_ja.add_official_japanese_labels(japanese_path, labels)

    assert count == 1
    assert labels == {
        "0000002": "existing label",
    }


def test_write_hpo_japanese_ttl(tmp_path):
    output_path = tmp_path / "HPO_ja.ttl"

    hp_ja.write_hpo_japanese_ttl(
        output_path,
        {
            "0000002": 'quote " label',
            "0000003": "backslash \\ label",
        },
    )

    assert output_path.read_text(encoding="utf-8") == (
        "@prefix obo: <http://purl.obolibrary.org/obo/> .\n"
        "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .\n\n"
        'obo:HP_0000002 rdfs:label "quote \\" label"@ja .\n\n'
        'obo:HP_0000003 rdfs:label "backslash \\\\ label"@ja .\n\n'
    )
