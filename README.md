# Odoo Documentation AI Translation Tools

This repository contains tools for translating Odoo documentation `.po` files using AI and fixing RST (reStructuredText) formatting problems.

These scripts were created to help translators speed up the Odoo documentation translation process.

---

## Features

* Batch translation of `.po` files using AI
* Reduces API cost by translating multiple strings at once
* Preserves Sphinx / RST syntax
* Fixes common formatting issues after translation

---

## Files

translate_po_batch_v1.py
→ Batch translation script for `.po` files

fix_rst_po_ver3.py
→ Fixes RST / Sphinx formatting problems

---

## How to run

Run the translation script:

python translate_po_batch_v1.py

Run the RST fixing script:

python fix_rst_po_ver3.py

---

## Workflow

1. Download a `.po` file from Weblate
2. Run the translation script
3. Run the RST fix script
4. Upload the corrected `.po` file back to Weblate

---

## Disclaimer

This tool is not affiliated with Odoo S.A.

Always review translations before submitting them.

---

## License

MIT License
