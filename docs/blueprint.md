# MaximoBRD

## Project Blueprint

---

# Purpose

This document describes the vision, requirements, constraints, preferred technologies, and implementation goals for MaximoBRD.

This document is intentionally solution-oriented but should not be treated as a rigid implementation specification.

The AI is expected to:

- Evaluate the proposed architecture
- Identify weaknesses and risks
- Suggest simplifications where appropriate
- Recommend implementation phases
- Define an MVP
- Produce a development roadmap before implementation begins

No code should be generated until a planning phase has been completed and approved.

---

# Product Vision

MaximoBRD is a desktop application designed for IBM Maximo consultants and business analysts.

The application ingests requirement-gathering artifacts chronologically from multiple sources and automatically generates a professionally structured Business Requirements Document (BRD).

The goal is to significantly reduce the time required to create BRDs while improving consistency, traceability, and Maximo-specific accuracy.

The generated document should be suitable as a consultant's first client-facing draft.

---

# Success Criteria

A consultant should be able to:

1. Create a project.
2. Upload requirement source material keeping in mind their creation timestamps for chronological understanding.
3. Generate a BRD.
4. Review and export the generated word document.

The resulting BRD should:

- Maintain traceability to source material.
- Reflect the selected Maximo version.
- Follow Maximo and consulting best practices.
- Require minimal manual rework.

---

# Target Users

Primary users:

- IBM Maximo consultants
- Enterprise Asset Management consultants
- Business analysts
- Solution architects

Common engagement types:

- Discovery workshops
- Requirement gathering sessions
- Functional design workshops
- BRD creation engagements
- Maximo assessments
- Digital transformation projects

---

# Core Principles

## Consultant First

The application exists to accelerate consulting deliverables.

## Local First

Files should remain on the user's machine whenever possible.

## Privacy First

Audio and video processing should occur locally before AI analysis.

## Provider Agnostic

The system should support multiple AI providers without requiring major architectural changes.

## Maximo Aware

Generated output should reflect the client's Maximo environment.

## Traceable

Requirements should maintain links to their originating sources.

---

# Functional Requirements

## Project Setup

Users must be able to:

- Create projects
- Define client name
- Define project name
- Define project date
- Select Maximo version
- Optionally upload a branding reference document
- Add supporting requirement artifacts (i.e., docs, excels, pdf, audio, video)

Supported versions:

- Maximo 7.6.0.x
- Maximo 7.6.1.x
- MAS 8.x
- MAS 9.x

---

## Requirement Sources

The application should support:

### Documents

- PDF
- DOCX
- TXT
- Markdown

### Spreadsheets

- XLSX
- XLS

### Audio

- MP3
- WAV
- M4A
- OGG

### Video

- MP4
- MOV
- WEBM

For each uploaded source:

- Store metadata
- Preserve timestamps
- Allow timestamp override
- Maintain source traceability

---

## AI Configuration

The application should support:

* Mainstream cloud-hosted AI models via user-provided API credentials
* Local AI models via Ollama or equivalent local inference providers

Users should be able to:

* Configure AI providers
* Store API credentials securely
* Select available models
* Test provider connectivity
* Change providers without affecting project data

The application should be designed around a provider-agnostic architecture.

API keys must never be stored in plaintext.

A Bring Your Own Key (BYOK) model is preferred.

---

# Maximo Intelligence

The application should understand the selected Maximo version and use that information when analyzing requirements.

The system should:

- Distinguish configuration from customization
- Identify implied requirements
- Highlight implementation risks
- Identify upgrade considerations
- Recommend native platform capabilities
- Suggest alternatives when requirements conflict with platform limitations

Version-specific knowledge should be maintained separately from application code.

---

# Maximo Version Awareness

The solution should support version-specific analysis for:

## Maximo 7.6.0.x

Traditional Java EE deployment.

Typical characteristics:

- WebSphere or WebLogic
- MBO customization
- Jython automation scripts
- Integration Framework usage
- Limited REST capabilities

---

## Maximo 7.6.1.x

Most common deployment in current enterprise environments.

Typical characteristics:

- Improved REST APIs
- Mature automation scripting
- MAF mobile support
- Common upgrade path to MAS

---

## MAS 8.x

Containerized deployment on OpenShift.

Typical characteristics:

- Maximo Manage
- API-first integrations
- Liberty runtime
- Suite applications such as Monitor, Predict and Health
- AppPoint licensing model

---

## MAS 9.x

Latest generation Maximo Application Suite deployment.

Typical characteristics:

- Enhanced AI capabilities
- Advanced Predict and Health functionality
- Improved data architecture
- Expanded suite integrations

---

# Requirement Processing Pipeline

The application should process information through logical stages.

Potential stages include:

1. Ingestion
2. Normalization
3. Domain Analysis
4. Requirement Enrichment
5. BRD Generation
6. Styling and Formatting

The planning phase should evaluate whether a multi-agent architecture is justified or whether a simpler approach would provide faster delivery and easier maintenance.

---

# Suggested Architecture Direction

Preferred technologies:

## Desktop

- Electron

## Frontend

- React
- Tailwind CSS

## Backend

- Python
- FastAPI

## Document Generation

- python-docx

## Spreadsheet Processing

- openpyxl

## PDF Processing

- PyMuPDF

## Audio Transcription

- Whisper

These technologies are preferred but may be challenged if significantly better alternatives exist.

---

# Branding Support

Users may optionally provide a reference DOCX.

The application should attempt to replicate:

- Typography
- Heading hierarchy
- Table styles
- Header and footer styling
- Logos
- Overall document appearance

The planning phase should assess the complexity and feasibility of this capability.

---

# User Experience Goals

The application should feel:

- Professional
- Fast
- Reliable
- Enterprise-grade
- Consultant-focused

The interface should prioritize workflow efficiency over visual complexity.

---

# Security Requirements

The application must:

- Store API keys securely
- Avoid plaintext credential storage
- Avoid logging sensitive information
- Support local processing where possible

A BYOK (Bring Your Own Key) model is preferred.

---

# Risks and Complexity Areas

High Risk:

- Document style cloning
- Long transcript processing
- Context window management
- Multi-provider AI orchestration

Medium Risk:

- Desktop packaging
- Progress streaming
- Large file handling

Low Risk:

- UI implementation
- Settings management
- Standard document ingestion

---

# Non-Goals

The application is not intended to become:

- A project management platform
- A requirements repository
- A SharePoint replacement
- A workflow engine
- A collaborative editing platform

---

# MVP Definition

The smallest viable version should allow a user to:

1. Create a project.
2. Upload documents.
3. Generate a BRD.
4. Export a DOCX.

Using a single AI provider.

Features such as:

- Branding extraction
- Multi-provider support
- Audio transcription
- Video transcription
- Advanced styling

may be deferred to later phases if necessary.

---

# Expected Planning Deliverables

Before implementation begins, the AI should provide:

1. Architecture review
2. Risk assessment
3. Complexity assessment
4. Recommended repository structure
5. Dependency analysis
6. MVP definition
7. Phase breakdown
8. Development roadmap
9. Milestone plan
10. Open questions

The planning phase should actively challenge assumptions and recommend simplifications where they improve delivery speed, maintainability, or product quality.

---

# Planning Instructions

Before generating any code:

- Review this document completely.
- Critically evaluate the proposed approach.
- Challenge unnecessary complexity.
- Recommend simplifications.
- Identify hidden risks.
- Propose a phased roadmap.
- Define the smallest practical MVP.
- Wait for approval before implementation.

