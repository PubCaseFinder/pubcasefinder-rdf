# PCF RDF Build Guide (Japanese)

## 概要

この文書は `C:\Users\shin\Documents\PCF_RDF` 作業フォルダで RDF 生成物を再作成する方法をまとめたガイドです。

現在の Java パッケージ名は `pubcasefinder_260415` です。

生成物の出力先は `pcf-rdf.properties` の `rdf.output.dir` を使用し、現在の既定値は `RDF/latest` です。

## 事前条件

以下が準備されている必要があります。

- JDK 21
- `data` フォルダ配下の入力リソース
- `tools/ncbi/datasets.exe`
- `tools/ncbi/dataformat.exe`
- `pcf-rdf.properties` の設定確認

現在の resource root の既定値は以下です。

- `data/NCBIGene`
- `data/MedGen`
- `data/Orphanet`
- `data/MONDO`
- `data/GenCC`
- `data/PanelSearch`
- `data/OMIM`
- `data/KEGG`
- `data/GeneReviews`
- `data/HPO`

必要に応じて `pcf-rdf.properties` の `*.dir` または `*.path` を変更し、別の場所を使用できます。

## 全体の実行順序

RDF 全体を生成する場合、以下の順序を推奨します。

1. `NCBIGeneSummaryHelper` (任意)
2. `NCBIHGNCGeneCatalog`
3. `DiseaseMetadataOMIM`
4. `DiseaseMetadataORDO`
5. `DiseasePhenotypeOMIM`
6. `DiseasePhenotypeORDO`
7. `DiseaseGeneOMIM`
8. `DiseaseGeneORDO`
9. `DiseaseGeneMONDO`
10. `DiseaseGeneNANDO`
11. `DiseaseGeneGenCC`
12. `HP_ja`

各プログラムの役割は次のとおりです。

- `NCBIGeneSummaryHelper`: NCBI summary キャッシュを生成。必要な場合のみ実行
- `NCBIHGNCGeneCatalog`: `all_gene.ttl` を生成
- `DiseaseMetadata*`: 疾患メタデータ TTL を生成
- `DiseasePhenotype*`: 疾患-表現型 TTL を生成
- `DiseaseGene*`: 疾患-遺伝子 TTL を生成
- `HP_ja`: HPO 日本語ラベル TTL を生成

## コンパイル方法

作業フォルダで以下のコマンドを実行して Java ソースをコンパイルします。

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\javac.exe' -encoding UTF-8 -d .codex-build *.java
```

## RDF 全体の生成方法

以下の PowerShell スクリプトを実行すると、全 RDF を順番に生成できます。

```powershell
$ErrorActionPreference='Stop'

if (Test-Path '.codex-build') {
    Remove-Item -LiteralPath '.codex-build' -Recurse -Force
}

New-Item -ItemType Directory -Path '.codex-build' | Out-Null

& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\javac.exe' -encoding UTF-8 -d .codex-build *.java

$classes = @(
  'pubcasefinder_260415.NCBIGeneSummaryHelper',
  'pubcasefinder_260415.NCBIHGNCGeneCatalog',
  'pubcasefinder_260415.DiseaseMetadataOMIM',
  'pubcasefinder_260415.DiseaseMetadataORDO',
  'pubcasefinder_260415.DiseasePhenotypeOMIM',
  'pubcasefinder_260415.DiseasePhenotypeORDO',
  'pubcasefinder_260415.DiseaseGeneOMIM',
  'pubcasefinder_260415.DiseaseGeneORDO',
  'pubcasefinder_260415.DiseaseGeneMONDO',
  'pubcasefinder_260415.DiseaseGeneNANDO',
  'pubcasefinder_260415.DiseaseGeneGenCC',
  'pubcasefinder_260415.HP_ja'
)

foreach ($class in $classes) {
    Write-Host "=== RUN $class ==="
    & 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build $class
}
```

実行後に一時コンパイルフォルダを削除する場合は次のコマンドを実行します。

```powershell
Remove-Item -LiteralPath '.codex-build' -Recurse -Force
```

## 任意実行可能な項目

`NCBIGeneSummaryHelper` は常に必須ではありません。

現在の構成では `NCBIHGNCGeneCatalog` は以下の順で gene summary 入力を探します。

1. `pcf-rdf.properties` の `ncbigene.summary.path`
2. `ncbigene.dir` 配下の `gene_summary.tsv.gz`
3. `ncbigene.dir` 配下の `gene_summary.tsv`
4. 上記がない場合のみ `datasets.exe` と `dataformat.exe` を使って summary を取得

したがって、以下のいずれかを満たす場合は `NCBIGeneSummaryHelper` を省略できます。

- `data/NCBIGene/latest/gene_summary.tsv` が既に存在する
- `data/NCBIGene/latest/gene_summary.tsv.gz` が既に存在する
- `pcf-rdf.properties` で `ncbigene.summary.path` を直接指定している

逆に、以下の場合は `NCBIGeneSummaryHelper` を先に実行することを推奨します。

- gene summary キャッシュが存在しない
- 最新の NCBI summary に更新したい
- ネットワーク接続可能な環境で summary を再取得したい

実運用では次のように考えると分かりやすいです。

- 通常の再生成: `NCBIGeneSummaryHelper` は省略可
- summary データ更新時: `NCBIGeneSummaryHelper` 実行推奨

## 個別実行方法

必要なプログラムだけ個別に実行することもできます。

例:

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build pubcasefinder_260415.NCBIHGNCGeneCatalog
```

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build pubcasefinder_260415.DiseaseGeneMONDO
```

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build pubcasefinder_260415.HP_ja
```

## 主な生成物

既定の出力先 `RDF/latest` には以下のファイルが生成されます。

- `all_gene.ttl`
- `OMIM.ttl`
- `Orphanet.ttl`
- `OMIM_HP_Association.ttl`
- `Orphanet_HP_Association.ttl`
- `OMIM_Gene_Association.ttl`
- `Orphanet_Gene_Association.ttl`
- `MONDO_Gene_Association.ttl`
- `NANDO_Gene_Association.ttl`
- `GenCC_Gene_Association.ttl`
- `HPO_ja.ttl`

## プログラム別説明

### 1. NCBIGeneSummaryHelper

役割:

- NCBI の `datasets.exe` と `dataformat.exe` を使って `gene_summary.tsv` キャッシュファイルを生成します。

出力:

- `data/NCBIGene/latest/gene_summary.tsv`

注意:

- NCBI API へのアクセスが必要なため、ネットワーク制限がある環境では失敗することがあります。
- 既に summary キャッシュファイルがある場合は必ずしも実行不要です。
- このプログラムは `all_gene.ttl` 生成のための補助ツールです。

### 2. NCBIHGNCGeneCatalog

役割:

- `Homo_sapiens.gene_info.gz`
- `gene_summary.tsv` または `gene_summary.tsv.gz`

を利用して、全遺伝子カタログ RDF を生成します。

補足:

- summary キャッシュがあれば `NCBIGeneSummaryHelper` なしでも実行できます。
- summary キャッシュがない場合は内部的に `datasets.exe` と `dataformat.exe` の実行を試みます。

出力:

- `RDF/latest/all_gene.ttl`

### 3. DiseaseMetadataOMIM

役割:

- OMIM 疾患メタデータ RDF を生成

出力:

- `RDF/latest/OMIM.ttl`

### 4. DiseaseMetadataORDO

役割:

- Orphanet 疾患メタデータ RDF を生成

出力:

- `RDF/latest/Orphanet.ttl`

### 5. DiseasePhenotypeOMIM

役割:

- OMIM 疾患-表現型 RDF を生成

出力:

- `RDF/latest/OMIM_HP_Association.ttl`

### 6. DiseasePhenotypeORDO

役割:

- Orphanet 疾患-表現型 RDF を生成

出力:

- `RDF/latest/Orphanet_HP_Association.ttl`

### 7. DiseaseGeneOMIM

役割:

- OMIM 疾患-遺伝子 RDF を生成

出力:

- `RDF/latest/OMIM_Gene_Association.ttl`

### 8. DiseaseGeneORDO

役割:

- Orphanet 疾患-遺伝子 RDF を生成

出力:

- `RDF/latest/Orphanet_Gene_Association.ttl`

### 9. DiseaseGeneMONDO

役割:

- MONDO 疾患-遺伝子 RDF を生成

出力:

- `RDF/latest/MONDO_Gene_Association.ttl`

### 10. DiseaseGeneNANDO

役割:

- NANDO 疾患-遺伝子 RDF を生成

出力:

- `RDF/latest/NANDO_Gene_Association.ttl`

### 11. DiseaseGeneGenCC

役割:

- GenCC 疾患-遺伝子 RDF を生成

出力:

- `RDF/latest/GenCC_Gene_Association.ttl`

### 12. HP_ja

役割:

- HPO 日本語 label RDF を生成

出力:

- `RDF/latest/HPO_ja.ttl`

## 運用メモ

- 入力ファイルの場所を変更する場合は、できるだけソース修正ではなく `pcf-rdf.properties` を先に変更してください。
- 全再生成前に `RDF/latest` の既存ファイルをバックアップするかどうかを決めてください。
- NCBI API に接続できない環境では、`gene_summary.tsv` を事前に用意しておくと `NCBIGeneSummaryHelper` を省略できます。

## 簡易確認コマンド

生成後に出力ファイル一覧を確認する場合:

```powershell
Get-ChildItem -Path 'RDF\latest' -File | Select-Object Name,Length,LastWriteTime
```

`gene_summary.tsv` の生成確認:

```powershell
Get-Item 'data\NCBIGene\latest\gene_summary.tsv'
```
