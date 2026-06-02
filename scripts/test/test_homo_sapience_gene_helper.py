from pathlib import Path

from package import homo_sapience_gene_helper


def test_main_uses_configured_source_and_output(mocker):
    config = {
        "ncbi_homosapience_gene_data_uri": "https://example.org/Homo_sapiens.gene_info.gz",
        "ncbigene_file_path": "data/source/NCBIGene/latest/Homo_sapiens.gene_info.gz",
    }
    mocker.patch.object(homo_sapience_gene_helper, "load_config", return_value=config)
    download = mocker.patch.object(
        homo_sapience_gene_helper,
        "download_homo_sapiens_gene_info",
    )

    homo_sapience_gene_helper.main()

    homo_sapience_gene_helper.load_config.assert_called_once_with("config.ini")
    download.assert_called_once_with(
        "https://example.org/Homo_sapiens.gene_info.gz",
        "data/source/NCBIGene/latest/Homo_sapiens.gene_info.gz",
    )


def test_download_homo_sapiens_gene_info_downloads_to_output_path(tmp_path, mocker):
    def fake_urlretrieve(url, filename):
        Path(filename).write_text("downloaded")
        return filename, None

    mocker.patch.object(
        homo_sapience_gene_helper.urllib.request,
        "urlretrieve",
        fake_urlretrieve,
    )

    output_path = tmp_path / "NCBIGene" / "latest" / "Homo_sapiens.gene_info.gz"
    result = homo_sapience_gene_helper.download_homo_sapiens_gene_info(
        "https://example.org/Homo_sapiens.gene_info.gz",
        output_path,
    )

    assert result == output_path
    assert output_path.read_text() == "downloaded"
