## {タイトル}
id: {00}
branch-slug: {slug}
github_issue:
status: draft
type: cleanup | fix | feat
対象: {変更・新規作成するファイルをすべて列挙。新規は (新規) を付記}
内容: {目的と概要のみ}
確認: `PYTHONPATH=src pytest -q`（pandas/numpy が環境に無ければ `nix-shell -p "python3.withPackages(ps: with ps; [pandas numpy pytest])" --run "PYTHONPATH=src pytest -q"`）

---

{仕様の詳細}
