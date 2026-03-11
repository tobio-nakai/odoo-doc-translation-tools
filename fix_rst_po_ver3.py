import re
import polib

INPUT_PO = "input.po"
OUTPUT_PO = "output.po"

# RST / Sphinx roles that must be preserved during translation
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
    Replace pattern matches in the text using tokens from source_tokens
    in left-to-right order.

    If the number of matches differs, only the common number of items
    will be replaced.
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
    Restore protected roles in msgstr using the roles from msgid.

    Example:
    :guilabel:`日本語` → :guilabel:`English`
    """
    msgid_tokens = extract_full_role_tokens(msgid)
    return replace_matches_by_order(msgstr, ROLE_PATTERN, msgid_tokens)


def restore_placeholders_from_msgid(msgid: str, msgstr: str) -> str:
    """
    Restore placeholders based on the original msgid.

    Example:
    Remaining %s columns → keep %s unchanged
    """
    msgid_tokens = extract_placeholders(msgid)
    return replace_matches_by_order(msgstr, PLACEHOLDER_PATTERN, msgid_tokens)


def restore_html_tags_from_msgid(msgid: str, msgstr: str) -> str:
    """
    Restore HTML tags according to the original msgid.

    Example:
    <strong>Delivery date</strong>
    """
    msgid_tokens = extract_html_tags(msgid)
    return replace_matches_by_order(msgstr, HTML_TAG_PATTERN, msgid_tokens)


def restore_missing_roles_from_msgid(msgid: str, msgstr: str) -> str:
    """
    If a role exists in msgid but disappears in msgstr,
    attempt to restore simple cases.

    Example:
      msgid  = Click :guilabel:`Send by Email` button.
      msgstr = :guilabel: Send by Email button...
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
        lambda m: msgid_roles[0].split("`")[0] + "`" if msgid_roles else m.group(0),
        fixed,
        count=1,
    )

    return fixed


def fix_inline_markup_spacing(text: str) -> str:
    """
    Fix spacing issues after inline markup elements.
    """

    # **text**word → **text** word
    text = re.sub(r"(\*\*[^*\n]+\*\*)(\S)", r"\1 \2", text)

    # *text*word → *text* word
    text = re.sub(r"(?<!\*)(\*[^*\n]+\*)(\S)", r"\1 \2", text)

    # :role:`text`word → :role:`text` word
    text = re.sub(
        r"(:(" + "|".join(PROTECTED_ROLES) + r"):`[^`]+`)(\S)",
        r"\1 \3",
        text,
    )

    # punctuation immediately followed by role
    text = re.sub(
        r"([、。．，；：])(:(" + "|".join(PROTECTED_ROLES) + r"):`)",
        r"\1 \2",
        text,
    )

    # HTML tag directly attached to text
    text = re.sub(r"(</?[A-Za-z][A-Za-z0-9]*(?:\s+[^<>]*?)?>)(\S)", r"\1 \2", text)

    # placeholder directly attached to alphabetic characters
    text = re.sub(r"(%(?:\([^)]+\))?[sdif])([A-Za-z])", r"\1 \2", text)

    return text


def normalize_spaces(text: str) -> str:
    """
    Normalize spacing.
    """
    text = re.sub(r"[ \t]{2,}", " ", text)

    lines = text.splitlines()
    lines = [line.strip() for line in lines]
    return "\n".join(lines)


def fix_rst(msgid: str, msgstr: str) -> str:
    """
    Version 3 processing flow:

    1. Restore roles based on msgid
    2. Restore placeholders
    3. Restore HTML tags
    4. Fix simple cases where roles disappeared
    5. Fix inline markup spacing
    6. Normalize spaces
    """
    if not msgstr:
        return msgstr

    fixed = msgstr

    fixed = replace_role_tokens_from_msgid(msgid, fixed)
    fixed = restore_placeholders_from_msgid(msgid, fixed)
    fixed = restore_html_tags_from_msgid(msgid, fixed)

    fixed = restore_missing_roles_from_msgid(msgid, fixed)

    fixed = fix_inline_markup_spacing(fixed)

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