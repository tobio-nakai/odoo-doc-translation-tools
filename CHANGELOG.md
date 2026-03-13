# Changelog

All notable changes to this project will be documented in this file.

This repository provides CLI tools for translating and post-processing
Odoo documentation `.po` files.

---

## v0.3.0

### translate_po_batch.py

Improved the AI translation pipeline.

- Refactor script structure for better maintainability
- Add bilingual (Japanese / English) comments
- Improve translation prompt for Odoo documentation context
- Add terminology guidance for ERP and accounting terms
- Use structured JSON output from the OpenAI API to prevent parsing errors
- Improve batch translation stability
- Add retry logic for API failures

### fix_rst_po.py

Improve RST post-processing tool.

- Rename `fix_rst_po_ver3.py` → `fix_rst_po.py`
- Add bilingual (Japanese / English) comments
- Improve code readability and structure
- Preserve protected Sphinx roles:
  - `:guilabel:`
  - `:menuselection:`
  - `:icon:`
  - `:ref:`
  - `:doc:`
- Restore placeholders such as `%s`, `%d`, `%(name)s`
- Restore HTML tags
- Fix spacing issues around inline RST markup

---

## v0.2.0

### translate_po_batch_v1.py

Translation quality improvements.

- Improve translation quality
- Add terminology guidance
- Use JSON output to prevent line-break parsing errors
- Add retry logic for OpenAI API failures

---

## v0.1.0

Initial release.

- Add `translate_po_batch_v1.py` for AI-based PO file translation
- Add `fix_rst_po_ver3.py` for post-processing translated PO files