# IDEA-010 Property Acquisition — Emergent starter pack

Prepared 4 September 2026 for Nick Brecciaroli.

## What this pack is

This pack authorises an initial private responsive-web prototype build. It does not authorise a public launch, paid data purchase, portal scraping, migration of the live Perth workflow, external agent contact, billing, native apps or production use of personal Gmail/Drive data.

The product remains IDEA-010. Commercial verdict remains RESEARCH FURTHER while the delivery gate is now OWNER APPROVED — INITIAL PRIVATE PROTOTYPE.

## Recommended upload order in Emergent

1. Upload this complete ZIP, or upload the two DOCX files plus the `concept-images` and `fixtures` folders.
2. Start a new web-app project and connect a new private GitHub repository using Emergent's secure integration. Do not paste credentials into chat.
3. Open `IDEA-010 Emergent Prompt Runbook` and run Prompt 00 first.
4. Review Emergent's implementation plan. It must identify unsupported substitutions, secrets and external services before coding.
5. Run prompts 01–07 in order. Do not combine the later integration/deployment prompts into the first build.

## Data access decision

Do not connect Emergent to the live Perth Property Acquisition Hub, Gmail label, portal accounts or scheduled tasks for the first build. The prototype sources are human reference only. Use the included synthetic fixtures.

After tenant isolation, authentication, audit, deletion and import rollback tests pass in staging, Nick may separately approve a dated read-only Hub export for migration rehearsal. Gmail OAuth and licensed feeds remain later gates.

## Reference links

- Current prototype specification: https://docs.google.com/document/d/1eLnseV33tXSvdTUsXy8SLuUevP77DbZE/edit
- Current user guide: https://docs.google.com/document/d/110w2_eavG3XUfZoou6Umu0X25uYc-XCd/edit
- Nationwide requirements proposal: https://docs.google.com/document/d/1be6tod1_SZwbnoDusrM05vKQn6EWd6CE/edit
- Live Perth Hub — reference only: https://docs.google.com/spreadsheets/d/1UJR65aOK9Ol86IGm6Sc_V0b0NfK432s0WezA9vtxxA0/edit
- Approved digest PDF reference: https://drive.google.com/file/d/1pjFGhBtqaLKRoonL2MDri5qEcn_balbX/view
- Complete concept-image folder: https://drive.google.com/drive/folders/1sXtcyWgCOfS1yM8X_guiXCSzFOyTYxss

## Required outputs from Emergent

- A working private preview with responsive desktop, phone and tablet layouts.
- Source in the connected private GitHub repository with meaningful milestone commits.
- Database migrations, seed/reset instructions and synthetic demo data.
- Automated tests for hard gates, scoring, tenancy, duplicate replay and draft safety.
- A requirements traceability report showing built, deferred and blocked items.
- No claim of production readiness until the final acceptance prompt passes.
