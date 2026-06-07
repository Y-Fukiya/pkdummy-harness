# External Tool Validation Guide

この文書は、Phoenix / NONMEM / nlmixr2 の実環境確認をrepo内の証跡として残すための手順です。

外部ツール本体、license、施設SOPはこのrepoに含めません。ここで確認するのは、fixture harnessが作ったCSVやtemplateを外部環境へ渡せるかです。

## Profiles

既定profile:

```text
external_validation/tool_profiles.yml
```

Windows用の記入例:

```text
external_validation/tool_profiles.windows.example.yml
```

施設環境ではexampleをコピーし、実際のpath、command、success_artifactsに合わせて編集してください。

## Probe

`--execute` なしでは、commandが存在するかを確認し、`EXTERNAL_TOOL_VALIDATION.yml` を作ります。

```bash
python tools/run_external_tool_validation.py \
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir \
  --out-dir outputs/external_validation_probe/minimal_aciclovir \
  --profile-yml external_validation/tool_profiles.yml
```

SKIPPED is not automatically a harness failure. SKIPPEDは、profileはあるが実行ファイルが見つからないという意味です。

## Execute

施設で実行許可された環境だけで `--execute` を使います。

```bash
python tools/run_external_tool_validation.py \
  --downstream-dir outputs/downstream_smoke_check/minimal_aciclovir \
  --out-dir outputs/external_validation_execute/minimal_aciclovir \
  --profile-yml external_validation/tool_profiles.yml \
  --tools nonmem,nlmixr2 \
  --execute
```

## Tool-specific notes

| Tool | What to configure | Evidence |
| --- | --- | --- |
| Phoenix | automation command, project/template, NCA CSV input | log, imported dataset, optional project output |
| NONMEM | `nmfe75` path/version, control stream, working directory | `.lst` in success_artifacts |
| nlmixr2 | Rscript path, package library, parser or estimation script | stdout/stderr log, optional R output |

`success_artifacts` は実行成功とみなすファイルです。NONMEMなら `.lst`、施設のPhoenix automationならproject outputやimport logなどを指定します。

## Manifest interpretation

`EXTERNAL_TOOL_VALIDATION.yml` の見方:

| Status | Meaning |
| --- | --- |
| `OK` | probeまたはexecuteが通った |
| `WARN` | optional profileで実行結果に確認事項がある |
| `SKIPPED` | optional profileの実行ファイルが見つからない |
| `FAILED` | required profile、実行失敗、またはsuccess_artifacts不足 |

この結果は外部ツール取り込み確認の証跡であり、clinical inferenceやdose selectionの妥当化ではありません。
