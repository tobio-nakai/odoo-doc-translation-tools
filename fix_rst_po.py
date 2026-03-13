import re
import polib

# ============================================
# 設定 / Configuration
# ============================================

# 入力POファイルのパス
# Path to the input PO file
INPUT_PO = "/Users/toshihio_nakai/Downloads/odoo-19-doc-finance-ar/odoo-19-doc-finance-ar-translated.po"

# 出力POファイルのパス
# Path to the output PO file
OUTPUT_PO = "/Users/toshihio_nakai/Downloads/odoo-19-doc-finance-ar/odoo-19-doc-finance-ar-translated.po-fixed.po"

# 翻訳で壊れやすいため保護対象にするRST / Sphinxロール
# RST / Sphinx roles to protect because translation often breaks them
PROTECTED_ROLES = ["guilabel", "menuselection", "icon", "ref", "doc"]

# 保護対象ロール全体を抽出するための正規表現
# Regex to capture full protected role tokens so they can be restored from msgid
ROLE_PATTERN = re.compile(
    r":(" + "|".join(PROTECTED_ROLES) + r"):`[^`]*`"
)

# printf形式のプレースホルダを保護するための正規表現
# Regex to preserve printf-style placeholders because translators/models may alter them
PLACEHOLDER_PATTERN = re.compile(
    r"%(?:\([^)]+\))?[sdif]|%\([^)]+\)[sdif]"
)

# HTMLタグを保護するための正規表現
# Regex to preserve HTML tags because markup corruption can break rendered output
HTML_TAG_PATTERN = re.compile(
    r"</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>]*?)?>"
)


def extract_full_role_tokens(text: str) -> list[str]:
    """
    テキストから保護対象ロール全体を抽出する
    Extract full protected role tokens from text
    """
    return [match.group(0) for match in ROLE_PATTERN.finditer(text)]


def extract_placeholders(text: str) -> list[str]:
    """
    テキストからプレースホルダを抽出する
    Extract placeholders from text
    """
    return [match.group(0) for match in PLACEHOLDER_PATTERN.finditer(text)]


def extract_html_tags(text: str) -> list[str]:
    """
    テキストからHTMLタグを抽出する
    Extract HTML tags from text
    """
    return [match.group(0) for match in HTML_TAG_PATTERN.finditer(text)]


def replace_matches_by_order(
    text: str,
    pattern: re.Pattern,
    source_tokens: list[str],
) -> str:
    """
    pattern に一致した箇所を、source_tokens の左から順番に置き換える
    Replace pattern matches using source_tokens in left-to-right order

    一致数が異なる場合でも共通件数ぶんだけ置換することで、
    完全一致しない翻訳結果でもできるだけ安全に復元する。
    If the counts differ, replace only the common number of items so recovery
    remains safe even when the translated output is imperfect.
    """
    matches = list(pattern.finditer(text))
    if not matches or not source_tokens:
        return text

    replacement_count = min(len(matches), len(source_tokens))

    parts = []
    last_index = 0

    for index in range(replacement_count):
        match = matches[index]
        parts.append(text[last_index:match.start()])
        parts.append(source_tokens[index])
        last_index = match.end()

    parts.append(text[last_index:])
    return "".join(parts)


def replace_role_tokens_from_msgid(msgid: str, msgstr: str) -> str:
    """
    msgid のロールを使って msgstr 内のロールを復元する
    Restore protected roles in msgstr using the roles found in msgid

    目的は翻訳でロール内部の文字列や構造が壊れた場合でも、
    元のマークアップを優先して安全に戻すこと。
    The goal is to prefer original markup from msgid when translation damages
    role content or structure.
    """
    msgid_tokens = extract_full_role_tokens(msgid)
    return replace_matches_by_order(msgstr, ROLE_PATTERN, msgid_tokens)


def restore_placeholders_from_msgid(msgid: str, msgstr: str) -> str:
    """
    msgid のプレースホルダを使って msgstr を補正する
    Restore placeholders in msgstr using the original placeholders from msgid

    %s や %(name)s が壊れると実行時エラーや表示崩れの原因になるため、
    翻訳内容より元の構文維持を優先する。
    Placeholder corruption can cause runtime or rendering issues, so original
    syntax is prioritized over translated variants.
    """
    msgid_tokens = extract_placeholders(msgid)
    return replace_matches_by_order(msgstr, PLACEHOLDER_PATTERN, msgid_tokens)


def restore_html_tags_from_msgid(msgid: str, msgstr: str) -> str:
    """
    msgid のHTMLタグを使って msgstr を補正する
    Restore HTML tags in msgstr using the original tags from msgid

    HTMLタグは表示や意味づけに影響するため、
    翻訳後のタグを信用せず元のタグを優先して戻す。
    HTML tags affect rendering and semantics, so original tags are restored
    instead of trusting translated output.
    """
    msgid_tokens = extract_html_tags(msgid)
    return replace_matches_by_order(msgstr, HTML_TAG_PATTERN, msgid_tokens)


def restore_missing_roles_from_msgid(msgid: str, msgstr: str) -> str:
    """
    msgid にあるロールが msgstr で消えた単純ケースを補正する
    Restore simple cases where a role exists in msgid but disappears in msgstr

    これは完全修復ではなく、AI翻訳でよくある
    ':guilabel: text' のような壊れ方を最小限救うための処理。
    This is not a full repair system; it targets common AI translation failures
    such as broken ':guilabel: text' patterns.
    """
    msgid_roles = extract_full_role_tokens(msgid)
    msgstr_roles = extract_full_role_tokens(msgstr)

    if not msgid_roles:
        return msgstr

    if len(msgid_roles) == len(msgstr_roles):
        return msgstr

    fixed = msgstr

    fixed = re.sub(
        r":(" + "|".join(PROTECTED_ROLES) + r"):\s+",
        lambda match: msgid_roles[0].split("`")[0] + "`" if msgid_roles else match.group(0),
        fixed,
        count=1,
    )

    return fixed


def fix_inline_markup_spacing(text: str) -> str:
    """
    インラインマークアップ周辺のスペース崩れを補正する
    Fix spacing issues around inline markup

    AI翻訳後は '**text**word' のようにマークアップ直後のスペースが
    消えやすいため、読みやすさとRST安全性のために整える。
    After AI translation, spaces after inline markup are often lost, so this
    fixes readability and helps preserve valid RST-style formatting.
    """
    # **text**word → **text** word
    # Insert a space after bold inline markup when it is directly attached to text
    text = re.sub(r"(\*\*[^*\n]+\*\*)(\S)", r"\1 \2", text)

    # *text*word → *text* word
    # Insert a space after italic inline markup when it is directly attached to text
    text = re.sub(r"(?<!\*)(\*[^*\n]+\*)(\S)", r"\1 \2", text)

    # :role:`text`word → :role:`text` word
    # Insert a space after protected roles when they are directly attached to text
    text = re.sub(
        r"(:(" + "|".join(PROTECTED_ROLES) + r"):`[^`]+`)(\S)",
        r"\1 \3",
        text,
    )

    # punctuation immediately followed by role
    # Add a space between punctuation and a protected role for readability
    text = re.sub(
        r"([、。．，；：])(:(" + "|".join(PROTECTED_ROLES) + r"):`)",
        r"\1 \2",
        text,
    )

    # HTML tag directly attached to text
    # Add a space after HTML tags when they are attached to following text
    text = re.sub(
        r"(</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>]*?)?>)(\S)",
        r"\1 \2",
        text,
    )

    # placeholder directly attached to alphabetic characters
    # Add a space after placeholders when they run into alphabetic text
    text = re.sub(
        r"(%(?:\([^)]+\))?[sdif])([A-Za-z])",
        r"\1 \2",
        text,
    )

    return text


def normalize_spaces(text: str) -> str:
    """
    余分な空白を正規化する
    Normalize spacing

    翻訳後に発生しやすい連続スペースや行頭行末の不要空白を除去して、
    差分確認とレビューをしやすくする。
    Removes repeated spaces and trims line edges to make diff review easier
    after translation.
    """
    text = re.sub(r"[ \t]{2,}", " ", text)

    lines = text.splitlines()
    lines = [line.strip() for line in lines]
    return "\n".join(lines)


def fix_rst(msgid: str, msgstr: str) -> str:
    """
    RST / Sphinxマークアップ補正のメイン処理
    Main processing flow for fixing RST / Sphinx markup

    処理順を固定する理由は、先に構文要素を戻してからスペース調整するほうが
    壊れにくく、レビュー結果も安定するため。
    The order is fixed because restoring structural markup first and normalizing
    spacing afterward is more stable and less error-prone.
    """
    if not msgstr:
        return msgstr

    fixed = msgstr

    # 1. ロール復元
    # 1. Restore protected roles
    fixed = replace_role_tokens_from_msgid(msgid, fixed)

    # 2. プレースホルダ復元
    # 2. Restore placeholders
    fixed = restore_placeholders_from_msgid(msgid, fixed)

    # 3. HTMLタグ復元
    # 3. Restore HTML tags
    fixed = restore_html_tags_from_msgid(msgid, fixed)

    # 4. 単純なロール消失ケースを補正
    # 4. Repair simple cases where roles disappeared
    fixed = restore_missing_roles_from_msgid(msgid, fixed)

    # 5. インラインマークアップ周辺のスペース補正
    # 5. Fix spacing around inline markup
    fixed = fix_inline_markup_spacing(fixed)

    # 6. 最終的な空白正規化
    # 6. Normalize spaces at the end
    fixed = normalize_spaces(fixed)

    return fixed


def process_po(input_po: str, output_po: str) -> None:
    """
    POファイル全体にRST補正を適用する
    Apply RST fixes to all translated entries in a PO file

    未翻訳エントリには触れず、msgstr があるものだけを対象にすることで、
    不要な差分発生を避ける。
    Only translated entries are processed to avoid unnecessary diffs on
    untranslated content.
    """
    po = polib.pofile(input_po)

    changed_count = 0

    for entry in po:
        if not entry.msgstr:
            continue

        original = entry.msgstr
        fixed = fix_rst(entry.msgid, entry.msgstr)

        if fixed != original:
            entry.msgstr = fixed
            changed_count += 1

    po.save(output_po)

    print(f"Done! fixed entries: {changed_count}")
    print(f"Saved to: {output_po}")


if __name__ == "__main__":
    process_po(INPUT_PO, OUTPUT_PO)