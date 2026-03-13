import json
import re
import time
from typing import List, Dict, Any

import polib
from openai import OpenAI

# ============================================
# 基本設定 / Basic configuration
# ============================================

# 入力POファイルのパス
# Path to the input PO file
INPUT_FILE = "input.po"

# 出力POファイルのパス
# Path to the output PO file
OUTPUT_FILE = "output.po"

# 対象言語
# Target language
TARGET_LANGUAGE = "Arabic"
# 例 / Examples:
# "Arabic"
# "Thai"
# "Japanese"
# "French"
# "Spanish"

# 1回の翻訳件数
# Number of entries per translation batch
BATCH_SIZE = 20

# 使用モデル
# Model name
MODEL_NAME = "gpt-4o-mini"

# 何バッチごとに途中保存するか
# Save progress every N batches
SAVE_EVERY_N_BATCHES = 1

# API失敗時の最大再試行回数
# Maximum retry count for API/parsing failures
MAX_RETRIES = 3

# 再試行前の待機秒数
# Waiting time before retry
RETRY_SLEEP_SECONDS = 2

# 既に翻訳済みのmsgstrをスキップするか
# Whether to skip entries that already have msgstr
SKIP_TRANSLATED = True

# 空のmsgidをスキップするか
# Whether to skip empty msgid entries
SKIP_EMPTY_MSGID = True


# ============================================
# OpenAIクライアント / OpenAI client
# ============================================

# OPENAI_API_KEY が環境変数に設定されている前提
# Assumes OPENAI_API_KEY is set in the environment
client = OpenAI()


# ============================================
# 言語別ルール / Language-specific rules
# ============================================

# 言語ごとの追加ルール
# Additional rules for each target language
LANGUAGE_RULES_MAP = {
    "Arabic": """
- Use clear, professional Modern Standard Arabic.
- Keep UI labels concise and natural.
- Be careful with right-to-left text.
- Preserve technical and accounting precision.
""".strip(),

    "Thai": """
- Use natural Thai suitable for software UI and technical documentation.
- Keep UI labels concise and readable.
- Preserve technical and accounting precision.
""".strip(),

    "Japanese": """
- Use natural Japanese suitable for ERP documentation.
- Keep UI labels concise and clear.
- Distinguish carefully between similar accounting terms.
- Preserve technical and accounting precision.
""".strip(),

    "French": """
- Use clear, professional French suitable for ERP documentation.
- Keep UI labels concise and natural.
- Preserve technical and accounting precision.
""".strip(),

    "Spanish": """
- Use clear, professional Spanish suitable for ERP documentation.
- Keep UI labels concise and natural.
- Preserve technical and accounting precision.
""".strip(),
}

# 言語別ルールが未定義のときの共通ルール
# Fallback rules when no language-specific rules are defined
DEFAULT_LANGUAGE_RULES = """
- Use clear, professional language suitable for ERP documentation.
- Keep UI labels concise and natural.
- Preserve technical and accounting precision.
""".strip()


# ============================================
# 用語ガイダンス / Terminology guidance
# ============================================

# 用語の区別ルール
# Guidance for distinguishing accounting/ERP terms
TERMINOLOGY_GUIDANCE = """
- Distinguish carefully between invoice, vendor bill, bill, payment, payment term, journal, account, tax reduction, tax computation, and cash discount.
- Keep terminology consistent across entries.
- Translate terminology appropriately for the target language and Odoo accounting context.
- Do not collapse distinct business terms into one generic term when the source distinguishes them.
- Prefer terminology natural for accounting and ERP documentation rather than casual prose.
""".strip()


# ============================================
# システムプロンプト生成 / System prompt builder
# ============================================

def get_language_specific_rules(target_language: str) -> str:
    """
    対象言語に対応する追加ルールを返す
    Return language-specific additional rules for the target language
    """
    return LANGUAGE_RULES_MAP.get(target_language, DEFAULT_LANGUAGE_RULES)


def build_system_prompt(target_language: str) -> str:
    """
    システムプロンプトを組み立てる
    Build the system prompt
    """
    language_rules = get_language_specific_rules(target_language)

    return f"""
You are a professional translator for Odoo ERP documentation.

Target language: {target_language}
Domain: Odoo documentation, especially Accounting and Finance
Style: Clear, professional, concise documentation style

Context rules:
- Translate in an ERP/accounting context, not as casual prose.
- Keep terminology consistent across entries.
- Prefer concise UI-friendly wording when labels appear.
- Distinguish accounting and ERP terms carefully.

Important terminology guidance:
{TERMINOLOGY_GUIDANCE}

Language-specific rules:
{language_rules}

Strict preservation rules:
- Preserve reStructuredText syntax exactly.
- Do not alter or translate role/directive names such as:
  :guilabel:, :menuselection:, :doc:, :ref:, :abbr:, :term:
- Preserve placeholders exactly:
  %s, %d, %(name)s, {{name}}, {{0}}, etc.
- Preserve HTML/XML tags exactly.
- Preserve markdown/reST emphasis and literals exactly:
  **bold**, *italic*, ``code``
- Preserve product names, module names, and technical identifiers where appropriate.
- Do not add explanations, notes, headings, or comments.
- Return only valid JSON.

Output format:
{{
  "translations": [
    {{
      "index": 1,
      "translation": "..."
    }}
  ]
}}
""".strip()


# ============================================
# ユーザーペイロード生成 / User payload builder
# ============================================

def build_user_payload(batch: List[polib.POEntry], target_language: str) -> str:
    """
    モデルへ渡すJSONペイロードを作る
    Build the JSON payload sent to the model
    """
    items = []

    for idx, entry in enumerate(batch, start=1):
        items.append({
            "index": idx,
            "text": entry.msgid
        })

    payload = {
        "task": f"Translate each text into {target_language} for Odoo documentation.",
        "items": items
    }

    return json.dumps(payload, ensure_ascii=False, indent=2)


# ============================================
# JSON抽出 / JSON extraction
# ============================================

def extract_first_json_object(text: str) -> Dict[str, Any]:
    """
    レスポンス文字列から最初のJSONオブジェクトを抽出する
    Extract the first JSON object from the response text
    """
    text = text.strip()

    # まず全文をJSONとして読む
    # First, try parsing the full text directly as JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 失敗したら最初のJSONブロックを抜き出す
    # If that fails, extract the first JSON block
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in model response.")

    json_str = match.group(0)
    return json.loads(json_str)


# ============================================
# バッチ翻訳 / Batch translation
# ============================================

def translate_batch(batch: List[polib.POEntry], target_language: str) -> List[str]:
    """
    1バッチを翻訳して翻訳文字列リストを返す
    Translate one batch and return a list of translated strings
    """
    system_prompt = build_system_prompt(target_language)
    user_payload = build_user_payload(batch, target_language)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_payload
                    }
                ]
            )

            content = response.choices[0].message.content or ""
            data = extract_first_json_object(content)

            translations = data.get("translations")
            if not isinstance(translations, list):
                raise ValueError("'translations' is not a list.")

            # index順に並べる
            # Sort by index
            translations_sorted = sorted(
                translations,
                key=lambda item: item.get("index", 999999)
            )

            result_texts = []
            for item in translations_sorted:
                translated = item.get("translation")
                if not isinstance(translated, str):
                    raise ValueError("Each translation item must have a string 'translation'.")
                result_texts.append(translated)

            # 件数一致チェック
            # Validate translation count
            if len(result_texts) != len(batch):
                raise ValueError(
                    f"Translation count mismatch. Expected {len(batch)}, got {len(result_texts)}."
                )

            return result_texts

        except Exception as e:
            print(f"[WARN] Batch translation failed (attempt {attempt}/{MAX_RETRIES}): {e}")

            if attempt == MAX_RETRIES:
                raise

            time.sleep(RETRY_SLEEP_SECONDS)

    raise RuntimeError("Unexpected error in translate_batch().")


# ============================================
# PO収集 / PO collection
# ============================================

def collect_entries_to_translate(po: polib.POFile) -> List[polib.POEntry]:
    """
    翻訳対象エントリを集める
    Collect entries that need translation
    """
    entries = []

    for entry in po:
        # 既に翻訳済みならスキップ
        # Skip already translated entries
        if SKIP_TRANSLATED and entry.msgstr:
            continue

        # 空msgidをスキップ
        # Skip empty msgid
        if SKIP_EMPTY_MSGID and not entry.msgid.strip():
            continue

        entries.append(entry)

    return entries


# ============================================
# 保存処理 / Save function
# ============================================

def save_po(po: polib.POFile, output_file: str) -> None:
    """
    POファイルを保存する
    Save the PO file
    """
    po.save(output_file)
    print(f"[INFO] Saved: {output_file}")


# ============================================
# メイン処理 / Main process
# ============================================

def main() -> None:
    """
    メイン処理
    Main entry point
    """
    # POファイルを読み込む
    # Load the PO file
    po = polib.pofile(INPUT_FILE)

    # 翻訳対象を集める
    # Collect entries that need translation
    entries_to_translate = collect_entries_to_translate(po)

    print(f"[INFO] Target language: {TARGET_LANGUAGE}")
    print(f"[INFO] Need translation: {len(entries_to_translate)}")

    if not entries_to_translate:
        print("[INFO] Nothing to translate.")
        save_po(po, OUTPUT_FILE)
        return

    batch_count = 0

    # バッチごとに翻訳する
    # Translate entries in batches
    for start in range(0, len(entries_to_translate), BATCH_SIZE):
        batch = entries_to_translate[start:start + BATCH_SIZE]
        end = start + len(batch)

        print(f"[INFO] Translating batch: {start} - {end}")

        translated_texts = translate_batch(batch, TARGET_LANGUAGE)

        # 翻訳結果を反映する
        # Apply translated results
        for entry, translated in zip(batch, translated_texts):
            entry.msgstr = translated

        batch_count += 1

        # 定期保存
        # Periodic save
        if batch_count % SAVE_EVERY_N_BATCHES == 0:
            save_po(po, OUTPUT_FILE)

    # 最終保存
    # Final save
    save_po(po, OUTPUT_FILE)

    print("[INFO] Done!")


if __name__ == "__main__":
    main()