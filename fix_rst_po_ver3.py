import re
import polib

INPUT_PO = "/Users/toshihio_nakai/Downloads/ODOOドキュメント翻訳/inventory_and_mrp/odoo-19-doc-inventory_and_mrp-vi/odoo-19-doc-inventory_and_mrp-vi.po_translated.po"
OUTPUT_PO = "/Users/toshihio_nakai/Downloads/ODOOドキュメント翻訳/inventory_and_mrp/odoo-19-doc-inventory_and_mrp-vi/odoo-19-doc-inventory_and_mrp-vi.po_translated.po_fixed.po"

# 保護対象のRST/Sphinx role
PROTECTED_ROLES = ["guilabel", "menuselection", "icon", "ref", "doc"]

ROLE_PATTERN = re.compile(
    r":(" + "|".join(PROTECTED_ROLES) + r"):`[^`]*`"
)

PLACEHOLDER_PATTERN = re.compile(
    r"%(?:\([^)]+\))?[sdif]|%\([^)]+\)[sdif]"
)

HTML_TAG_PATTERN = re.compile(
    r"</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>]*?)?>"
)


def extract_full_role_tokens(text: str):
    return [m.group(0) for m in ROLE_PATTERN.finditer(text)]


def extract_placeholders(text: str):
    return [m.group(0) for m in PLACEHOLDER_PATTERN.finditer(text)]


def extract_html_tags(text: str):
    return [m.group(0) for m in HTML_TAG_PATTERN.finditer(text)]


def replace_matches_by_order(text: str, pattern: re.Pattern, source_tokens: list[str]) -> str:
    """
    text 内の pattern マッチ部分を、source_tokens で左から順に置換する。
    数がズレる場合は共通個数だけ置換。
    """
    matches = list(pattern.finditer(text))
    if not matches or not source_tokens:
        return text

    replacements = min(len(matches), len(source_tokens))

    parts = []
    last_index = 0

    for i in range(replacements):
        m = matches[i]
        parts.append(text[last_index:m.start()])
        parts.append(source_tokens[i])
        last_index = m.end()

    parts.append(text[last_index:])
    return "".join(parts)


def replace_role_tokens_from_msgid(msgid: str, msgstr: str) -> str:
    """
    msgstr 内の protected role を、msgid の role で左から順に置換。
    :guilabel:`日本語` → :guilabel:`English`
    """
    msgid_tokens = extract_full_role_tokens(msgid)
    return replace_matches_by_order(msgstr, ROLE_PATTERN, msgid_tokens)


def restore_placeholders_from_msgid(msgid: str, msgstr: str) -> str:
    """
    placeholder を原文準拠に戻す。
    例: 残り%s列 の %s を保護
    """
    msgid_tokens = extract_placeholders(msgid)
    return replace_matches_by_order(msgstr, PLACEHOLDER_PATTERN, msgid_tokens)


def restore_html_tags_from_msgid(msgid: str, msgstr: str) -> str:
    """
    HTMLタグを原文準拠に戻す。
    例: <strong>配送日</strong>
    """
    msgid_tokens = extract_html_tags(msgid)
    return replace_matches_by_order(msgstr, HTML_TAG_PATTERN, msgid_tokens)


def restore_missing_roles_from_msgid(msgid: str, msgstr: str) -> str:
    """
    msgid に role があるのに msgstr に role が消えている場合、
    単純なケースだけ補う。
    例:
      msgid  = Click :guilabel:`Send by Email` button.
      msgstr = :guilabel: メールで送信 ボタン...
    のような壊れ方に対して、最低限 role を元に戻しやすくする。
    """
    msgid_roles = extract_full_role_tokens(msgid)
    msgstr_roles = extract_full_role_tokens(msgstr)

    if not msgid_roles:
        return msgstr

    # すでに数が合っていれば何もしない
    if len(msgid_roles) == len(msgstr_roles):
        return msgstr

    fixed = msgstr

    # :guilabel: の後に空白だけで本文が続く壊れ方を補正
    fixed = re.sub(
        r":(" + "|".join(PROTECTED_ROLES) + r"):\s+",
        lambda m: msgid_roles[0].split("`")[0] + "`" if msgid_roles else m.group(0),
        fixed,
        count=1,
    )

    return fixed


def fix_inline_markup_spacing(text: str) -> str:
    """
    インラインマークアップの直後に文字がくっつく問題を修正
    """

    # **text**word -> **text** word
    text = re.sub(r"(\*\*[^*\n]+\*\*)(\S)", r"\1 \2", text)

    # *text*word -> *text* word
    text = re.sub(r"(?<!\*)(\*[^*\n]+\*)(\S)", r"\1 \2", text)

    # :role:`text`word -> :role:`text` word
    text = re.sub(
        r"(:(" + "|".join(PROTECTED_ROLES) + r"):`[^`]+`)(\S)",
        r"\1 \3",
        text,
    )

    # 句読点の直後に role
    # 例: 、:guilabel:`Name` -> 、 :guilabel:`Name`
    text = re.sub(
        r"([、。．，；：])(:(" + "|".join(PROTECTED_ROLES) + r"):`)",
        r"\1 \2",
        text,
    )

    # HTMLタグ直後の直結
    # 例: </strong>配送日 -> </strong> 配送日
    text = re.sub(r"(</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>]*?)?>)(\S)", r"\1 \2", text)

    # placeholder 直後の直結はそのままでもよいが、
    # 英数記号が不自然にくっつく場合だけ空白を補う
    text = re.sub(r"(%(?:\([^)]+\))?[sdif])([A-Za-z])", r"\1 \2", text)

    return text


def normalize_spaces(text: str) -> str:
    """
    スペースの整形
    """
    # 連続スペースを1つに
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 行頭・行末の余計なスペース削除（各行ごと）
    lines = text.splitlines()
    lines = [line.strip() for line in lines]
    return "\n".join(lines)


def fix_rst(msgid: str, msgstr: str) -> str:
    """
    ver3:
    1. role を原文準拠で復元
    2. placeholder を復元
    3. HTMLタグを復元
    4. role消失の軽微ケース補正
    5. spacing 修正
    6. スペース整形
    """
    if not msgstr:
        return msgstr

    fixed = msgstr

    # 原文準拠に戻す
    fixed = replace_role_tokens_from_msgid(msgid, fixed)
    fixed = restore_placeholders_from_msgid(msgid, fixed)
    fixed = restore_html_tags_from_msgid(msgid, fixed)

    # role が部分的に壊れたケースを軽く補正
    fixed = restore_missing_roles_from_msgid(msgid, fixed)

    # spacing 修正
    fixed = fix_inline_markup_spacing(fixed)

    # 最後に軽く整形
    fixed = normalize_spaces(fixed)

    return fixed


def process_po(input_po: str, output_po: str):
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