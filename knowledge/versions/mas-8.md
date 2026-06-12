# IBM Maximo Application Suite (MAS) 8.x — Maximo Manage Knowledge Base

This document covers **Maximo Manage on MAS 8.x** — the first generation of the Maximo Application Suite. MAS 8 introduced the OpenShift-based suite architecture, AppPoint licensing, and Maximo Mobile. MAS 8.11 (released October 2023) is the final 8.x release; IBM's strategic direction and active development have moved to MAS 9.x, and 8.x engagements today are predominantly **upgrade-from-7.6 landings** or **stepping stones toward MAS 9**.

## Platform Overview

Maximo Manage is the Enterprise Asset Management application inside the IBM Maximo Application Suite — the direct successor to Maximo 7.6 and the application where the majority of EAM consulting work takes place. Functionally, Manage on MAS 8.x carries the complete Maximo 7.6 EAM capability set forward: the data model, applications, workflow engine, escalations, Integration Framework, and security model are recognisably the same product.

What changed in MAS 8 is everything *around* the application:

- **Runs on Red Hat OpenShift** (Kubernetes container platform), not WebSphere. Manage runs as containers (pods) using the IBM Liberty application server. The database (IBM Db2, Oracle, or SQL Server) remains external to the cluster.
- **Suite packaging**: Manage is one of several suite applications sharing MAS Core services (Suite Administration, single identity, licensing). Other suite apps include Monitor, Health, Predict, Visual Inspection, and Assist — each separately enabled and consuming AppPoints.
- **AppPoint licensing**: a shared pool of license points consumed by user type (Limited, Base, Premium) and by enabled applications. This replaced 7.6's authorized/concurrent user licenses and must be analysed in every BRD.
- **MAS Core identity**: users are administered at the suite level and synchronised into Manage (LDAP, SAML/OIDC federation). Manage Security Groups still control what users can do once provisioned.
- **Java 8 runtime**: Manage 8.x server-side code and customisations run on Java 8 — one reason 7.6-era Java customisations often carry into MAS 8 with less friction than into MAS 9.1 (which requires Java 17).

Version timeline (suite → notable Manage milestones): MAS 8.4 (early 2021) was the first release to include Maximo Manage; 8.6–8.8 (2021–2022) matured Maximo Mobile and the Role Based Applications; 8.10 (mid 2023) and 8.11 (October 2023) are the common landing versions for late 7.6 migrations. All 8.x releases are on a path to end of support — confirm the client's version and IBM support dates at the start of the engagement, and treat "stay on 8.x long-term" as a risk to flag.

## Deployment Model

Deployment mode determines which customisation methods are available. Establish it first in every engagement.

**Self-Managed (customer-managed OpenShift)** — the on-premises equivalent. Full access to Database Configuration, Application Designer, automation scripts, and the Integration Framework. Java customisation is technically possible but requires building custom container images and re-applying them on every Manage update — IBM strongly discourages it. Direct database access is the client's own responsibility.

**IBM-Managed (IBM runs OpenShift, client runs Manage)** — configuration tools and automation scripts are available; Java customisation and container image changes are not supported through IBM; no direct production database access.

**MAS SaaS (IBM manages everything)** — most restrictive: Database Configuration, Application Designer, Workflow Designer, automation scripts (Jython/JavaScript), escalations, and supported Integration Framework configuration are allowed. Java MBO extensions, custom Java cron tasks, custom Java processing classes, container image customisation, and direct production database access are **not** supported.

Infrastructure implications to surface in BRDs: OpenShift/Kubernetes administration skills, container networking, persistent storage, and certificate management replace traditional WebSphere administration. Sizing is expressed in OpenShift worker nodes/cores. For self-managed clients coming from 7.6, this skills gap is itself a project risk.

## Customization Mechanisms

In order of preference for MAS 8.x:

1. **Database Configuration** — add attributes, objects, relationships, domains (ALN, NUMERIC, SYNONYM, CROSSOVER, TABLE), auditing, and e-signatures. Same tool and concepts as 7.6. "Apply Configuration Changes" may trigger pod restarts; on managed/SaaS deployments this can be restricted to maintenance windows.
2. **Application Designer** — Classic UI changes: add/move fields, tabs, sections, signature options, conditional UI, clone applications. **Applies to Classic applications only** — it cannot configure Role Based Applications (RBA) or Maximo Mobile.
3. **Automation Scripts** (Jython / Nashorn JavaScript on Java 8) — the primary business-logic mechanism, and the SaaS-safe replacement for most Java customisation. Launch points: Object, Attribute, Action, Custom Condition, Integration, Timer. Scripts can also be exposed as REST endpoints.
4. **Workflow Designer + Escalations + Communication Templates** — routing, approvals, background monitoring, notifications. Identical conceptual model to 7.6.
5. **Maximo Application Framework (MAF) configuration** — for RBA applications and Maximo Mobile: expose data-model attributes on screens, configure offline data scope, barcode behaviour, push triggers. Noticeably less mature on 8.x than 9.x; complex mobile UI changes may exceed what MAF configuration supports. Custom React components are not supported on SaaS.
6. **Java customisation** — last resort, self-managed only, via custom container image layers. Flag as a risk in any BRD; it complicates every subsequent update and the eventual MAS 9 upgrade (Java 8 → Java 17 recompilation).

## Integration Patterns

The Integration Framework carries over from 7.6 with a REST-first emphasis:

- **REST/OSLC JSON APIs** for all core Manage objects — the preferred method for new integrations and the channel Maximo Mobile itself uses. The API Keys application manages per-user/application access tokens.
- **Object Structures, Enterprise Services (inbound), Publish Channels (outbound)** — the classic MIF building blocks, all still present. Continuous queue processing via JMS or, on newer 8.x, Kafka for high-volume async integration.
- **Integration automation scripts** replace Java processing classes on Object Structures, Enterprise Services, and Publish Channels — the SaaS-compatible transformation/routing mechanism.
- **Invocation Channels** for synchronous outbound calls from workflow or UI actions.
- **Migration note**: 7.6-era SOAP web services and bespoke servlet integrations should be re-platformed to REST during the move to MAS; flag any SOAP dependency in the BRD as redesign work, not lift-and-shift.
- **External systems commonly integrated**: ERP financials (SAP, Oracle EBS) for GL/PO/invoice flows, SCADA/historians for meter readings, GIS (ESRI ArcGIS for service addresses and map views), identity providers (LDAP/Azure AD via MAS Core).

## Native vs Custom — decision guidance

The evaluation sequence for every requirement on MAS 8.x:

1. **Native configuration first** — can Database Configuration, Application Designer, domains, conditional UI, workflow, escalations, or SLAs meet it? Most "we customised this in 7.6" items turn out to be configurable.
2. **Automation scripts second** — business rules, validations, field defaulting, status logic, integration transformation. SaaS-safe and upgrade-friendly.
3. **REST API integration third** — when the logic belongs in an external system, integrate rather than extend.
4. **Java customisation last** — only on self-managed deployments, only when nothing above fits, and always flagged as a risk with its container-rebuild maintenance burden and Java 17 recompilation cost at the MAS 9 upgrade made explicit.

SaaS rule of thumb for BRDs: any requirement whose 7.6 answer was "custom Java" must be re-stated as either an automation-script design, a configuration design, or an explicit out-of-scope/risk item.

Mobile-specific guidance: if a requirement touches field work, decide early whether it targets Maximo Mobile (MAF-configured, offline-capable, strategic) — Maximo Anywhere is not supported on MAS and any Anywhere customisation inventory becomes migration scope.

## Common Module Capabilities (WO, ASSET, INV, PURCH, PM, SR)

Functionally equivalent to Maximo 7.6 across the core modules — existing 7.6 functional knowledge applies directly. Headlines per module:

- **Work Orders (WO)**: full lifecycle (WAPPR → APPR → INPRG → COMP → CLOSE, configurable), job plans with hierarchical tasks, labor/material/service/tool plans, safety plans, routes, failure reporting (Failure Class → Problem → Cause → Remedy), multi-asset work orders, parent/child hierarchies with cost rollup, Assignment Manager. Key objects: WORKORDER, WPLABOR, WPITEM, LABTRANS, MATRECTRANS, FAILUREREPORT.
- **Assets (ASSET)**: asset register with hierarchy and cost rollup, rotating assets tied to item masters, classifications/specifications, continuous-gauge-characteristic meters, condition monitoring with action limits that auto-create work orders, asset templates. Key objects: ASSET, ASSETSPEC, ASSETMETER, MEASUREPOINT, LOCATION.
- **Inventory (INV)**: item master (material/service/tool items), multi-storeroom balances with condition codes, reorder points/EOQ/ABC, reservations from WO material plans, issues/returns/transfers/adjustments, physical counts, Inventory Usage documents (ENTERED → STAGED → SHIPPED → COMPLETE). Key objects: ITEM, INVENTORY, INVUSE, STORELOC, INVRESERVE.
- **Purchasing (PURCH)**: full procure-to-pay — PR → RFQ → PO → Receipt → Invoice, purchase/price/blanket contracts driving PO pricing, centralised purchasing across sites, receipt inspection and rotating-item serialisation. Key objects: PR, PO, RFQ, INVOICE, RECEIPT, CONTRACT.
- **Preventive Maintenance (PM)**: time/meter/seasonal/combined triggers, job-plan sequences per cycle, Master PMs propagating to linked PMs, PM forecasting for capacity planning. Key objects: PM, PMSEQ, PMFORECAST.
- **Service Requests (SR)**: SR/Incident/Problem ticketing, SLAs with contact/response/resolution commitments and escalation monitoring, Solutions knowledge base, self-service portal for request creation. Key objects: SR, INCIDENT, PROBLEM, SLA, SOLUTION.

Cross-cutting: multi-org/multi-site, GL account structures on all cost transactions, Security Groups with signature options/data restrictions/attribute security, Start Centers with KPI and result-set portlets, BIRT operational reporting, Cognos for dashboards (license-dependent on 8.x), Maximo Mobile apps (Technician, Inspections, Service Requests, Approvals — earliest versions matured across 8.6–8.11).

## Upgrade / Migration Considerations

**From Maximo 7.6 to MAS 8.x** (the dominant 8.x engagement type):

- This is a **re-platform, not an in-place upgrade**: new OpenShift infrastructure, database migrated/upgraded, then Manage activated against it. IBM's Maximo Application Suite Migration tooling assists the database move.
- **Java customisation inventory** is the single biggest effort driver. Each item is re-evaluated: drop (now native), rewrite as automation script (preferred), or carry as container-image customisation (self-managed only, discouraged).
- **Maximo Anywhere → Maximo Mobile**: Anywhere is not supported on MAS. Mobile scope must be re-implemented via MAF configuration; app.xml customisations do not carry over.
- **Integrations**: SOAP/legacy interfaces re-platformed to REST/OSLC; queue infrastructure moves to suite-managed JMS/Kafka.
- **Reports**: BIRT reports generally migrate with version-compatibility checks; custom report libraries need review.
- **Identity**: authentication moves to MAS Core (LDAP/SAML/OIDC); plan user provisioning, group mapping, and VPN/SSO design.
- **Licensing**: convert 7.6 entitlements to AppPoints; model consumption by user mix before contract commitment.

**From MAS 8.x to MAS 9.x** (increasingly the reason 8.x appears in a BRD): in-suite upgrade rather than re-platform, but plan for the **Java 17 transition** (MAS 9.1) — recompile any custom Java, regression-test automation scripts (Nashorn behaviour changes), verify OpenShift version prerequisites, and review deprecated suite apps. New build work on 8.x should be written upgrade-safe: automation scripts and configuration only, no new Java.

## Known Platform Limitations

- **End of support horizon**: 8.11 is the last 8.x release; active development (new RBA features, Mobile improvements, AI capabilities) targets MAS 9. Long-lived requirements written against 8.x should note the 9.x upgrade explicitly.
- **Application Designer cannot touch RBA/Mobile screens** — two UI paradigms, two configuration toolsets; MAF configuration on 8.x is less capable than on 9.x, so complex mobile UI requirements may be infeasible without upgrading.
- **Java customisation is effectively unavailable on SaaS/IBM-Managed**, and on self-managed it imposes container rebuilds on every update.
- **Maximo Mobile maturity varies by 8.x level**: early 8.x Mobile lacked features field teams expect (work queue self-assignment, full offline parity); validate the specific Mobile app capability against the client's exact MAS level rather than assuming Technician-app parity with 9.x.
- **Maximo Anywhere and the 7.6 Everyplace/legacy mobile options are unsupported** — no transitional mobile option other than Maximo Mobile.
- **AppPoint ceilings**: enabling additional suite applications (Monitor, Health, Predict) and Premium-user features (e.g., Mobile with certain entitlements) consumes the shared AppPoint pool — a licensing constraint that can silently invalidate a requirement's feasibility.
- **OpenShift version coupling**: each 8.x level supports a specific OpenShift band; infrastructure currency work (cluster upgrades) is recurring operational scope clients new to containers often miss.
- **Start Center / Operational Dashboard gap**: the RBA Operational Dashboard on 8.x is early; clients expecting a modernised landing experience largely still rely on classic Start Centers.
