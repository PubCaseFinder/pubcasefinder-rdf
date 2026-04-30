# PCF RDF Build Guide

## 개요

이 문서는 `C:\Users\shin\Documents\PCF_RDF` 작업 폴더에서 RDF 산출물을 다시 생성하는 방법을 정리한 문서입니다.

현재 Java 패키지명은 `pubcasefinder_260415`입니다.

기본 산출물 출력 폴더는 `pcf-rdf.properties`의 `rdf.output.dir` 설정값을 따르며, 현재 기본값은 `RDF/latest`입니다.

## 사전 조건

다음 조건이 준비되어 있어야 합니다.

- JDK 21 설치
- `data` 폴더 아래 입력 리소스 준비
- `tools/ncbi/datasets.exe`
- `tools/ncbi/dataformat.exe`
- `pcf-rdf.properties` 설정 확인

현재 리소스 root는 기본적으로 아래 경로를 사용합니다.

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

필요하면 `pcf-rdf.properties`에서 `*.dir` 또는 `*.path` 값을 바꿔 다른 경로를 사용할 수 있습니다.

## 전체 실행 순서

전체 RDF 생성은 아래 순서로 진행하는 것을 권장합니다.

1. `NCBIGeneSummaryHelper` (선택)
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

이 순서의 의미는 다음과 같습니다.

- `NCBIGeneSummaryHelper`: NCBI summary 캐시 생성, 필요할 때만 실행
- `NCBIHGNCGeneCatalog`: `all_gene.ttl` 생성
- `DiseaseMetadata*`: 질병 메타데이터 TTL 생성
- `DiseasePhenotype*`: 질병-표현형 TTL 생성
- `DiseaseGene*`: 질병-유전자 TTL 생성
- `HP_ja`: HPO 일본어 label TTL 생성

## 컴파일 방법

작업 폴더에서 아래 명령으로 전체 Java 소스를 컴파일합니다.

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\javac.exe' -encoding UTF-8 -d .codex-build *.java
```

## 전체 RDF 생성 방법

작업 폴더에서 아래 PowerShell 스크립트를 실행하면 전체 RDF를 순서대로 생성할 수 있습니다.

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

## 선택 실행 가능 항목

`NCBIGeneSummaryHelper`는 항상 필수는 아닙니다.

현재 구조에서 `NCBIHGNCGeneCatalog`는 아래 순서로 gene summary 입력을 찾습니다.

1. `pcf-rdf.properties`의 `ncbigene.summary.path`
2. `ncbigene.dir` 아래의 `gene_summary.tsv.gz`
3. `ncbigene.dir` 아래의 `gene_summary.tsv`
4. 위 파일이 없을 때만 `datasets.exe`와 `dataformat.exe`를 사용해 summary를 직접 조회

즉 다음 조건 중 하나를 만족하면 `NCBIGeneSummaryHelper`는 생략 가능합니다.

- 이미 `data/NCBIGene/latest/gene_summary.tsv`가 존재하는 경우
- 이미 `data/NCBIGene/latest/gene_summary.tsv.gz`가 존재하는 경우
- `pcf-rdf.properties`에서 `ncbigene.summary.path`로 summary 파일을 직접 지정한 경우

반대로 아래 상황에서는 `NCBIGeneSummaryHelper`를 먼저 실행하는 것이 좋습니다.

- gene summary 캐시 파일이 없는 경우
- 최신 NCBI summary로 갱신하고 싶은 경우
- 네트워크 가능한 환경에서 summary를 새로 받아와야 하는 경우

실무적으로는 다음처럼 이해하면 됩니다.

- 평소 재생성: `NCBIGeneSummaryHelper` 생략 가능
- summary 데이터 갱신 시: `NCBIGeneSummaryHelper` 실행 권장

실행이 끝난 뒤 임시 컴파일 폴더를 지우려면 아래 명령을 실행합니다.

```powershell
Remove-Item -LiteralPath '.codex-build' -Recurse -Force
```

## 개별 실행 방법

필요한 프로그램만 개별 실행할 수도 있습니다.

예시:

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build pubcasefinder_260415.NCBIHGNCGeneCatalog
```

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build pubcasefinder_260415.DiseaseGeneMONDO
```

```powershell
& 'C:\Program Files\Eclipse Adoptium\jdk-21.0.10.7-hotspot\bin\java.exe' -cp .codex-build pubcasefinder_260415.HP_ja
```

## 생성되는 주요 산출물

기본 출력 폴더 `RDF/latest`에는 아래 파일들이 생성됩니다.

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

## 프로그램별 설명

### 1. NCBIGeneSummaryHelper

역할:

- NCBI `datasets.exe`와 `dataformat.exe`를 사용해 `gene_summary.tsv` 캐시 파일을 생성합니다.

출력:

- `data/NCBIGene/latest/gene_summary.tsv`

주의:

- NCBI API 접근이 필요하므로 네트워크가 막혀 있으면 실패할 수 있습니다.
- 이미 summary 캐시 파일이 있으면 반드시 실행할 필요는 없습니다.
- 이 프로그램은 `all_gene.ttl` 생성을 위한 보조 도구입니다.

### 2. NCBIHGNCGeneCatalog

역할:

- `Homo_sapiens.gene_info.gz`
- `gene_summary.tsv` 또는 `gene_summary.tsv.gz`

를 사용해 전체 유전자 카탈로그 RDF를 생성합니다.

보조 설명:

- summary 캐시 파일이 이미 있으면 `NCBIGeneSummaryHelper` 없이도 실행 가능합니다.
- summary 캐시 파일이 없으면 내부적으로 `datasets.exe`, `dataformat.exe`를 사용하려고 시도합니다.

출력:

- `RDF/latest/all_gene.ttl`

### 3. DiseaseMetadataOMIM

역할:

- OMIM 질병 메타데이터 RDF 생성

출력:

- `RDF/latest/OMIM.ttl`

### 4. DiseaseMetadataORDO

역할:

- Orphanet 질병 메타데이터 RDF 생성

출력:

- `RDF/latest/Orphanet.ttl`

### 5. DiseasePhenotypeOMIM

역할:

- OMIM 질병-표현형 RDF 생성

출력:

- `RDF/latest/OMIM_HP_Association.ttl`

### 6. DiseasePhenotypeORDO

역할:

- Orphanet 질병-표현형 RDF 생성

출력:

- `RDF/latest/Orphanet_HP_Association.ttl`

### 7. DiseaseGeneOMIM

역할:

- OMIM 질병-유전자 RDF 생성

출력:

- `RDF/latest/OMIM_Gene_Association.ttl`

### 8. DiseaseGeneORDO

역할:

- Orphanet 질병-유전자 RDF 생성

출력:

- `RDF/latest/Orphanet_Gene_Association.ttl`

### 9. DiseaseGeneMONDO

역할:

- MONDO 질병-유전자 RDF 생성

출력:

- `RDF/latest/MONDO_Gene_Association.ttl`

### 10. DiseaseGeneNANDO

역할:

- NANDO 질병-유전자 RDF 생성

출력:

- `RDF/latest/NANDO_Gene_Association.ttl`

### 11. DiseaseGeneGenCC

역할:

- GenCC 질병-유전자 RDF 생성

출력:

- `RDF/latest/GenCC_Gene_Association.ttl`

### 12. HP_ja

역할:

- HPO 일본어 label RDF 생성

출력:

- `RDF/latest/HPO_ja.ttl`

## 운영 팁

- 입력 파일 경로를 바꾸려면 가능하면 소스 수정 대신 `pcf-rdf.properties`를 먼저 수정합니다.
- 전체 재생성 전에는 `RDF/latest` 기존 파일 백업 여부를 결정합니다.
- NCBI API 접속이 제한된 환경에서는 `gene_summary.tsv`를 미리 준비해두면 `NCBIGeneSummaryHelper`를 건너뛸 수 있습니다.

## 빠른 점검 명령

생성 후 결과 파일 목록만 확인하려면:

```powershell
Get-ChildItem -Path 'RDF\latest' -File | Select-Object Name,Length,LastWriteTime
```

`gene_summary.tsv` 생성 여부를 확인하려면:

```powershell
Get-Item 'data\NCBIGene\latest\gene_summary.tsv'
```
