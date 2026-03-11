import polib
from openai import OpenAI

client = OpenAI()

INPUT_FILE = "input.po"
OUTPUT_FILE = "output.po"

BATCH_SIZE = 20

po = polib.pofile(INPUT_FILE)

entries_to_translate = []

for entry in po:
    if entry.msgstr:
        continue

    text = entry.msgid.strip()

    if text:
        entries_to_translate.append(entry)

print(f"Need translation: {len(entries_to_translate)}")

for i in range(0, len(entries_to_translate), BATCH_SIZE):

    batch = entries_to_translate[i:i+BATCH_SIZE]

    texts = []
    for idx, entry in enumerate(batch):
        texts.append(f"{idx+1}. {entry.msgid}")

    prompt = "\n".join(texts)

    print(f"Translating batch {i} - {i+len(batch)}")

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": """Translate to Indonesian for Odoo documentation.

Rules:
- Preserve reStructuredText syntax
- Do not translate :guilabel:, :menuselection:, :doc:, :ref:
- Preserve placeholders like %s %d %(name)s
- Preserve HTML tags
"""
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0
    )

    result = response.choices[0].message.content.strip().split("\n")

    for entry, line in zip(batch, result):

        translated = line.split(".",1)[1].strip() if "." in line else line
        entry.msgstr = translated

    if i % 100 == 0:
        po.save(OUTPUT_FILE)

po.save(OUTPUT_FILE)

print("Done!")
