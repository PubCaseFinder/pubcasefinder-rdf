from pathlib import Path

from package import homo_sapience_gene_helper


def test_download_homo_sapiens_gene_info(tmp_path, mocker):
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
