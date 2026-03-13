# Odooドキュメント AI翻訳ツール

![Odoo AI Translation Pipeline](images/pipeline.png)

Odoo documentation の `.po` ファイルを  
AIで翻訳し、RST（reStructuredText）構文の問題を修正するためのツールです。

このスクリプトは、Odooドキュメント翻訳の作業を効率化するために作られました。

---

# 主な機能

- `.po` ファイルのバッチ翻訳
- 複数文字列をまとめて翻訳することで API コストを削減
- Sphinx / RST 構文を保持
- 以下の特殊ロールを保護


:ref:
:doc:
:guilabel:
:menuselection:


- 翻訳後に発生しやすいフォーマット崩れを自動修正

---

# スクリプト

## translate_po_batch_v1.py

OpenAI API を使用して `.po` エントリをバッチ翻訳します。

主な機能

- バッチ翻訳
- APIコスト最適化
- 未翻訳エントリの安全な処理

使用例

```bash
python translate_po_batch_v1.py input.po output.po
fix_rst_po_ver3.py

翻訳後の .po ファイルに対して
RST / Sphinx フォーマットの問題を修正します。

使用例

python fix_rst_po_ver3.py input.po output.po
翻訳ワークフロー例

Odoo documentation を翻訳する場合の典型的な流れ

original.po
   ↓
translate_po_batch_v1.py
   ↓
translated.po
   ↓
fix_rst_po_ver3.py
   ↓
clean_translated.po
必要環境

Python 3.9 以上

必要ライブラリ

polib
openai

インストール

pip install polib openai
このプロジェクトの目的

Odoo documentation の翻訳は手作業では非常に時間がかかります。

このツールは次のことを目的としています。

翻訳作業の自動化

API コストの削減

Sphinx ドキュメントの構文エラー防止

ライセンス

MIT License（推奨）

作者

GitHub
https://github.com/tobio-nakai