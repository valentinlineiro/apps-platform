---
id: DOC-APP-EXC-001
title: Exam Corrector Application
audience: [human, ai]
last_updated: 2026-04-17
tags: [exam-corrector, omr, opencv, ai, flask, angular]
source_of_truth: true
related: [DOC-CON-001, DOC-APP-POR-001]
---

# Exam Corrector Application

## Purpose
The Exam Corrector is an AI-powered OMR (Optical Mark Recognition) system that automates the process of detecting and scoring exam sheets from images and PDFs.

## When to use
Use this document when working on the OpenCV image processing pipeline, modifying scoring rules, or updating the batch processing logic.

## Content

### Backend (Flask + OpenCV)
The backend processes images and PDFs to detect answer grids and score them based on templates.

#### Correction Pipeline
1. **`load_and_crop`**: OpenCV perspective-corrects the sheet to a fixed 900x1100 canvas.
2. **`detectar_bboxes_cv`**: Detects the answer grid using contour analysis and 1D clustering (cached).
3. **`corregir_con_omr`**: ECC alignment and per-option ink classifier (blank/selected/uncertain).
4. **`scoring_service`**: Applies configurable scoring rules to determine the final mark.

#### Key Endpoints
- `POST /exam-corrector/start`: Start async correction job.
- `GET /exam-corrector/status/<job_id>`: Poll job progress.
- `POST /exam-corrector/batch/start`: Start batch processing for ZIPs/PDFs.
- `GET /exam-corrector/batch/result/<batch_id>`: Export CSV results.

#### Persistence
- **`uploads/jobs.db`**: SQLite database for job tracking.
- **`uploads/templates/`**: Storage for user-defined exam templates.
- **`uploads/scoring_rules.json`**: Scoring configurations.

### Frontend (Angular)
The frontend provides a user-friendly interface for uploading exams, monitoring progress, and viewing results.
- **`exam-corrector-page.component.ts`**: Main UI for uploads, polling, and batch results.
- **`services/exam-corrector-api.service.ts`**: HTTP client for the OMR API.

## References
- [System Architecture](../../concepts/architecture.md)
- [Coding Standards](../../how-to/coding-standards.md)

## Change log
- **2026-04-17**: Moved to `apps/exam-corrector/` and standardized.
