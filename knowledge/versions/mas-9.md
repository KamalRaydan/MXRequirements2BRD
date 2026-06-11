# IBM Maximo Application Suite (MAS) 9.x — Maximo Manage Knowledge Base

## Overview

This document focuses exclusively on **Maximo Manage**, the Enterprise Asset Management application within the IBM Maximo Application Suite. Maximo Manage is the direct successor to Maximo 7.6 and is the application where the majority of EAM consulting work takes place.

MAS 9.0 was released June 2024. MAS 9.1 was released June 2025. All suite components share the same version number from 9.0 onwards.

---

## Platform Architecture

Maximo Manage runs on **Red Hat OpenShift** (Kubernetes-based container platform). This is a fundamental architectural departure from Maximo 7.6's Java EE application server model.

```
Cloud / On-Premises Infrastructure
          ↓
Red Hat OpenShift Cluster
          ↓
MAS Core (Suite Administration, Identity, AppPoint Licensing)
          ↓
Maximo Manage (EAM Application — Liberty Application Server in containers)
          ↓
Database: IBM Db2 / Oracle / Azure SQL (external, not containerised)
```

Maximo Manage runs as a set of containers (pods) on OpenShift. The application server is IBM Liberty (lightweight Java EE/Jakarta EE server). The database is external to the cluster.

Infrastructure teams need OpenShift/Kubernetes skills, container networking, persistent storage, and certificate management — skills distinct from traditional WAS administration.

---

## Deployment Modes and SaaS vs On-Premises

Deployment mode critically determines which customisation methods are available. This must be established at the start of every engagement.

### Self-Managed (Customer Manages OpenShift)
The client owns and manages the OpenShift infrastructure and the MAS deployment. This is the on-premises equivalent in the MAS world.

**Customisation capabilities:**
- Database Configuration — full access
- Application Designer — full access (classic apps)
- MAF/Maximo Application Framework — full access (RBA apps)
- Automation Scripts — full access (Jython, JavaScript)
- Java customisation — technically possible, but IBM's position is that it is strongly discouraged. Java customisations require container image customisation, significantly complicating upgrades and IBM support.
- Integration Framework — full access
- Direct database access — allowed (client's responsibility)

### IBM-Managed (IBM Manages OpenShift — Managed Service)
IBM manages the OpenShift infrastructure; the client manages the Maximo Manage application and its configuration.

**Customisation capabilities:**
- Database Configuration — allowed
- Application Designer — allowed
- Automation Scripts — allowed
- Java customisation — restricted. IBM does not support or troubleshoot Java customisations in managed environments. Container image customisation is not permitted through IBM.
- Direct database access — not permitted to production

### IBM Maximo Application Suite SaaS (IBM Manages Everything)
IBM manages all infrastructure, platform, and application updates. This is the most restrictive but lowest-overhead deployment model. IBM applies updates on IBM's schedule.

**Allowed on IBM MAS SaaS:**
- Database Configuration (adding attributes, objects, domains, relationships)
- Application Designer (UI modifications, signature options, conditional UI for classic apps)
- Automation Scripts — Jython and JavaScript (the primary extension mechanism)
- Workflow Designer
- Escalation configuration
- Integration Framework (Enterprise Services, Publish Channels, Object Structures via supported configuration)
- REST API integrations (inbound and outbound)
- Classification, Domain, Security Group management
- MAF configuration for Role Based Applications (within supported bounds)

**Not Supported / Restricted on IBM MAS SaaS:**
- Java MBO class extensions — no IBM support for debugging or troubleshooting
- Custom Java classes for cron tasks — not supported
- Custom action type "Custom Class" or "Command Line Executable" — not supported
- Java processing classes on Object Structures for integration — automation scripts recommended instead
- Direct database access to production environment — not permitted
- Container image customisation — not permitted
- EAR-equivalent (custom application deployment) — not applicable in MAS SaaS model

**Practical implication for BRDs:** When the client is on IBM SaaS, every requirement that would traditionally require Java customisation must be re-evaluated. The question is always: can this be achieved with Automation Scripts, configuration, or API integration? If yes, proceed. If no, flag as a risk or out-of-scope item for SaaS deployment.

---

## User Interface Paradigms in Maximo Manage

Maximo Manage has two coexisting UI technologies. A BRD should clarify which the client is using for each area of functionality.

### Classic Maximo UI
The traditional browser interface carried forward from Maximo 7.6. All core EAM applications (Work Order Tracking, Assets, Inventory, Purchasing, etc.) operate in this interface. Configured using **Application Designer**. Uses server-side rendering with a Java-based presentation layer.

### Role Based Applications (RBA) / Maximo Application Framework (MAF)
Modern React-based UI built on the IBM Maximo Application Framework. RBA applications have a distinctly different look and feel. They are configured through MAF tooling, not Application Designer. Most new applications added since MAS 8.x are RBA. Maximo Mobile apps are also built on MAF.

Examples of RBA applications in Manage:
- Work Orders (RBA — modernised WO tracking, still under development)
- Work Approvals (RBA)
- Operational Dashboard
- Workflow Assignments (RBA)
- Reliability Strategies
- Asset Manager (RBA — mobile)
- Scheduling Dashboard / Dispatching Dashboard
- API Keys
- Work Queue Manager

**Important distinction for customisation:** You cannot use Application Designer to configure RBA applications. Application Designer works only on Classic UI applications.

---

## Core Functional Modules — Deep Reference

### Work Order Management

Identical foundational capability to Maximo 7.6. Full work order lifecycle management.

**Work Order Types:** Work Order, Activity (child of a ticket), Change, Release. Corrective, Preventive, Inspection, Modification, Safety, Emergency are configured via the WORKTYPE domain.

**Work Order Lifecycle:** WAPPR → APPR → WMATL → WSCH → INPRG → COMP → CLOSE. Status transitions are configurable. WOSTATUS domain values define valid statuses.

**Work Planning:**
- Labor plans (craft, skill level, planned hours, estimated start/finish)
- Material plans (items from storeroom, with reservations against available balance)
- Service plans (outside contractor services by service item or standard service)
- Tool plans (tool items with hourly charge rates)
- Safety plans (automatically applied via job plan link — Hazards, Precautions, Lock Out/Tag Out)

**Job Plans:** Work order templates. Hierarchical tasks supported. A task can reference another job plan (multi-level). Job Plans applied manually or automatically on PM generation.

**Routes:** Define ordered sets of assets/locations for rounds, inspections, and multi-stop maintenance work. Each route stop can have an individual job plan.

**Failure Reporting:** Four-level hierarchy (Failure Class → Problem → Cause → Remedy). Reported at work order completion or in the field via Maximo Mobile. Drives reliability analysis.

**Multi-Asset / Multi-Location:** A single work order references multiple assets and locations (e.g., a lubrication work order covering 20 pump assets in one shift).

**Work Order Hierarchy:** Parent-child work order structures. Costs roll up from child to parent.

**Assignments:** Labor and crews assigned to work orders and their tasks via Assignment Manager (Classic) or Graphical Assignment (Maximo Scheduler).

**Key Objects:** WORKORDER, WOACTIVITY, WPLABOR, WPITEM, WPSERVICE, WPTOOL, LABTRANS, MATRECTRANS, TOOLTRANS, FAILUREREPORT, MULTIASSETLOCCI

### Asset Management

**Asset Register:** Unique asset number, description, vendor, manufacturer, serial number, installation date, purchase date and cost, warranty expiry, criticality, and priority.

**Asset Hierarchy:** Parent-child asset relationships. Supports cost and maintenance history rollup. Hierarchy linked to location hierarchy.

**Rotating Assets:** Assets linked to an Item Master record. Individual serial-numbered units tracked through their lifecycle — storeroom, installation location, repair, disposal.

**Specifications:** Classification hierarchy applied to assets adds structured technical attributes (e.g., Motor: Power = 55kW, Frame Size = D160). Essential for asset querying, condition monitoring, and Reliability Strategies.

**Meters:** Continuous (running hours, cycles, odometer), Gauge (temperature, vibration, pressure), Characteristic (oil quality, condition rating). Meter readings drive PM generation and Condition Monitoring alerts.

**Condition Monitoring:** Measurement points defined for gauge or characteristic meters. Action limits trigger automatic work order creation when a reading breaches the limit.

**Asset Templates:** Templates for creating multiple similar assets with predefined meters, spare parts, and maintenance schedules. Bulk asset creation. Changes to a template can be propagated to all linked assets.

**Reliability Strategies:** Library of 800+ asset types with predefined failure modes and mitigating activities. Consultants and reliability engineers can search this library and apply proven strategies to client assets without building from scratch.

**Linear Assets:** (Available via Linear Assets add-on or in MAS Manage for infrastructure clients.) Assets positioned along a linear network using chainage/mileage references. Work orders and condition monitoring linked to linear positions.

**Key Objects:** ASSET, ASSETSPEC, ASSETMETER, METERREADING, LOCATION, LOCATIONSPEC, MEASUREPOINT, ASSETMNTSKD, ASSET (parent-child via ASSETANCESTOR)

### Locations

Location hierarchy represents the physical or functional structure of a facility. Assets are installed at locations.

**Location Types:** Operating (assets installed here, work performed here), Storeroom, Labor, Repair Facility (accepts mobile assets for maintenance).

**Location Hierarchy:** Systems → Functional Locations → Sub-locations → Equipment positions.

**Service Addresses:** Postal addresses linked to locations. Support for map integration (ESRI ArcGIS). Used for Work Zone assignment and geographic dispatch.

**BIM Integration:** Building Information Models (COBie data) can be imported and linked to Locations and Assets. 3D BIM viewer available from Location, Asset, and Work Order records.

### Preventive Maintenance

**PM Records:** Schedule recurring work for an asset, location, or route. PMs generate work orders automatically.

**Frequency Triggers:**
- Time-based (every N days, weeks, months, years)
- Meter-based (every N hours/cycles/kilometres)
- Combined (time or meter, whichever comes first — "either/or" or "both")
- Seasonal (specific calendar months)

**Sequences:** Apply different job plans on different PM cycles (e.g., monthly = basic inspection job plan, annual = full overhaul job plan). Sequences can be defined by occurrence number or by the trigger type.

**Master PM:** Template linked to a rotating item type. Generates PM records for all assets/locations linked to that item. Changes to the Master PM propagate to linked PMs.

**PM Forecasting:** Generate predicted future PM dates for capacity planning, shutdown scheduling, and resource loading.

**PM Optimisation:** Integration with Maximo Scheduler to level PM workload against resource availability.

**Key Objects:** PM, PMSEQ, PMFORECAST, PMPOLICY

### Inventory Management

**Item Master:** Material items (stocked spare parts), Service items (non-stocked services), Tool items (charged at hourly rates, optionally rotating). Item Assembly Structures (IAS) define spare parts hierarchies.

**Storerooms:** Inventory is held in storeroom locations. Multiple storerooms per site. Inter-site and inter-organisation transfers supported.

**Inventory Records:** Item-storeroom combination with current balance, reorder point, reorder quantity, EOQ, ABC classification, primary vendor, and unit cost. Condition code-level balances supported.

**Reservations:** Work order material plans create reservations against storeroom balances. Drives procurement when stock is insufficient.

**Transactions:** Issues (to work orders), Returns (from work orders), Transfers (between storerooms via Inventory Usage), Adjustments (physical count reconciliation).

**Count Books:** Define sets of items for regular physical counting. Items can be selected by classification, ABC class, location, and other criteria.

**Physical Counts:** Count actual balances and reconcile against system balances. Variance reporting. Supports cycle counting (not all items counted at once).

**Inventory Usage Document:** Workflow-enabled inventory transaction document for staging, issuing, and transferring items. Used for inter-storeroom logistics. Status-tracked: ENTERED → STAGED → SHIPPED → COMPLETE.

**Key Objects:** ITEM, INVENTORY, INVUSE, INVUSELINESPLIT, MATRECTRANS, STORELOC, INVRESERVE, ITEMSTRUCT, STOREROOM, COUNTBOOK

### Purchasing and Procurement

Same core capability as Maximo 7.6. Full procure-to-pay cycle.

**PR → RFQ → PO → Receiving → Invoice** is the standard procurement flow.

**Purchase Contracts, Price Contracts, Blanket Contracts** drive pricing on POs.

**Centralised Purchasing:** One site raises and approves POs; multiple sites receive against those POs.

**Key Objects:** PR, PO, POCOST, RFQ, RFQBID, INVOICE, RECEIPT, CONTRACT

### Contracts

Full contract management across all contract types: Purchase, Price, Blanket, Lease/Rental, Labor Rate, Warranty, Service, Master.

Warranty contracts link to assets/locations and generate alerts or work orders when warranty expiry approaches.

Labor Rate Contracts define craft rates for outside labor (contractors). Outside labor hours reported on work orders are costed against the contract rates.

### Labor and Resources

**Person → Labor → Craft → Crew** is the resource hierarchy.

**Labor Records:** Linked to a Person. Craft and skill level assignments. Internal charge rates and premium pay rates. Qualification tracking with expiry date monitoring.

**Qualifications:** Certificates, licences, and trade qualifications required for specific crafts. Expiry dates tracked. Maximo validates qualifications when assigning labor to work orders (configurable enforcement).

**Crews:** Groups of labor assembled from Crew Types (templates). Crew positions define required craft and qualifications. Tool assets assigned to crew tool positions.

**Work Zones (new in MAS):** Geographic zone definitions. Labor and crews are associated with zones. Used by Graphical Assignment (Maximo Scheduler) for proximity-based dispatch — routing field work to the nearest available technician.

**Key Objects:** PERSON, LABOR, CRAFT, LABORCRAFTRATE, QUALIFICATION, LABORQUAL, CREW, CREWTYPE, WORKZONE

### Service Desk

Full IT-style service management coexisting with EAM work management.

**Ticket Types:** Service Request (SR), Incident, Problem. Activities are child records of any ticket type.

**Service Request Lifecycle:** NEW → QUEUED → INPROG → RESOLVED → CLOSED.

**SLA Framework:** Service Level Agreements applied to ticket types. Commitments define target contact, response, and resolution times. Escalations monitor progress and trigger notifications as targets approach.

**Solutions:** Knowledge base of documented resolutions searchable by all users and by self-service portal users.

**Self-Service Portal:** End users create Service Requests and Desktop Requisitions. Configurable service categories. Self-service users search Solutions before raising requests.

**Key Objects:** TKTEMPLATE, SR, INCIDENT, PROBLEM, SOLUTION, SLA, SLACOMMITMENT

### Financial

**Chart of Accounts:** Multi-segment GL code structure. Validated combinations defined per Organisation. Carried on work orders, POs, invoices, and inventory transactions for financial integration.

**Cost Management:** Project task-based cost tracking. Work orders reference project tasks and accumulate costs by project.

**Budget Reporting:** Budget versus actual versus committed variance analysis by GL account, location, or asset.

**Currency and Exchange Rates:** Multi-currency organisations. Exchange rates maintained per organisation.

### Security and Access Control

**Security Groups:** Define the access profile. Users are assigned to multiple Security Groups — permissions are additive (most permissive wins).

**Application Access:** Grant or deny access to each application per Security Group.

**Signature Options:** Named permissions within an application controlling specific actions. Defined in Application Designer (Classic) or MAF configuration (RBA). Granted in Security Groups.

**Data Restrictions:** Row-level record filtering. Restrict a Security Group to see only records matching specified attribute values.

**Attribute-Level Security:** Make individual fields read-only or hidden per Security Group.

**Conditional UI:** Show/hide fields, sections, tabs based on runtime conditions.

**MAS Suite-Level User Management:** In MAS, users are created and managed at the MAS Suite Administration level, not within Manage. Users are provisioned via:
- LDAP synchronisation
- SCIM 2.0 from identity providers (Azure Entra ID, Okta, Ping Identity)
- OIDC / SAML federation
- Multiple identity providers supported per MAS instance (MAS 9.0+)
- Custom LDAP attribute mapping for user data synchronisation (MAS 9.0+)

Users synchronised to Manage are then assigned to Security Groups within Manage.

**Key Objects:** MAXGROUP, GROUPAPPLICATION, APPLICATIONAUTH, SIGNOPTION, GROUPRESTRICT

### Workflow Engine

Identical conceptual model to Maximo 7.6.

**Workflow Designer:** Graphical drag-and-drop workflow builder. Multi-step routing, approvals, notifications, branching.

**Workflow Launch Points:** Manual (user-initiated), automatic (status change or record creation), timer-based.

**Actions in Workflow:** Set value, change status, custom class (restricted on SaaS), automation script action (preferred on SaaS), send email.

**Roles:** Dynamic resolution to a person or person group based on record data. Custom roles can be created via automation scripts.

**Escalations:** Background monitoring tasks. Detect conditions (e.g., high-priority work order not assigned within 1 hour) and trigger actions or notifications on schedule.

**Communication Templates:** Email templates with bind variables resolved from record data. Used by workflow actions and escalations. Support rich text, attachments.

### Integration Framework

**Same core architecture as Maximo 7.6 but REST-first in MAS.**

**REST APIs:** OSLC/JSON-based APIs for all core Manage objects. Preferred integration method. Used by Maximo Mobile, external applications, and custom integrations.

**Enterprise Services:** Inbound data ingestion. Data from external systems (SAP, Oracle, SCADA, etc.) sent to Manage object structures.

**Publish Channels:** Outbound data publication. Manage pushes events to external systems on record changes.

**Object Structures:** Define the integration data schema. A single message can include a Work Order plus its Plans, Tasks, and related data.

**API Keys Application (RBA):** Manage REST API access keys per user or application. Available in Manage.

**Invocation Channels:** Synchronous outbound calls to external services. Called from workflow or UI actions. Returns data back to Manage for processing.

**AppConnect:** IBM's low-code integration platform for MAS. Pre-built connectors to SAP, Salesforce, Workday, ServiceNow, and others. Preferred over custom middleware for common integrations.

**Integration Automation Scripts:** Replace Java processing classes on Object Structures, Enterprise Services, and Publish Channels. Allows scripted transformation and routing without Java on SaaS.

---

## Making Changes — Configuration and Customisation Reference

### Database Configuration

Same tool and concepts as Maximo 7.6.

**Adding Attributes:** Add fields to existing Maximo objects. Specify data type, length, domain, searchable status, audit status. Apply Configuration Changes to generate DDL.

**Adding Objects:** Create new tables with relationships to existing objects. Required for significant extensions to the data model.

**Domains:** Manage dropdown value lists. ALN (text), NUMERIC, SYNONYM (internal/display value mapping), CROSSOVER (field-to-field copying), TABLE (look-up from object), NUMERICRANGE.

**Auditing:** Enable attribute and object-level auditing. Before/after values, user, and timestamp recorded in audit tables.

**Electronic Signatures:** Require re-authentication on attribute change for regulatory compliance scenarios.

**Apply Configuration Changes:** Must be run after database configuration changes. In MAS, this also updates the OpenShift-deployed application and may require pod restarts. Managed SaaS environments may have restricted windows for applying configuration changes.

### Application Designer (Classic UI Applications Only)

Application Designer in Manage is functionally identical to Maximo 7.6. All the same capabilities apply: adding/removing fields, configuring tabs and sections, defining signature options, conditional UI, cloning applications.

**Export/Import XML:** Export presentation XML for version control. Import to migrate configurations across environments (Dev → Test → Production). On IBM SaaS, exporting and version-controlling presentation XML is strongly recommended because IBM controls the upgrade process and changes may be overwritten.

**Key difference from 7.6:** Application Designer does NOT configure Role Based Applications (RBA) or Maximo Mobile apps. Those require MAF tooling.

### Maximo Application Framework (MAF) — RBA Configuration

MAF is the React-based UI framework used for Role Based Applications and Maximo Mobile. Configuration is done through the MAF configuration tools, not Application Designer.

**What MAF Configuration Allows:**
- Add attributes from the Manage data model to RBA screens
- Modify field labels and layout within supported bounds
- Configure which data is fetched and displayed
- Define offline data models (which records are downloaded to mobile)
- Configure push notification triggers
- Configure barcode scanning behaviour

**Limitations of MAF Configuration:**
- Less flexible than Application Designer — you can add fields but cannot freely rearrange the UI layout in the same way
- Custom React components are not supported on IBM SaaS
- Some MAF configuration is reserved for IBM-developed capabilities

**Note for BRDs:** When a requirement involves modifying the look and feel or adding fields to Maximo Mobile apps, the question is whether the required attribute is available in the underlying Manage object structure (if yes, usually configurable) or whether it requires a new custom attribute (must be added via Database Configuration first, then exposed via MAF).

### Automation Scripts

Automation Scripts in Manage operate identically to Maximo 7.6 in concept. Key differences in MAS 9.x:

**MAS 9.1 Java 17:** All automation scripts run on Java 17. Scripts using Nashorn JavaScript APIs that were valid on Java 8/11 may behave differently. Scripts using the Mozilla Rhino compatibility layer may experience performance issues. Review and test all scripts when upgrading to MAS 9.1.

**Supported Languages in MAS:** JavaScript (Nashorn/OpenJDK Nashorn in MAS 9.1), Jython. Other JSR223-compliant engines can be added but are not standard.

**Launch Points:** Object, Attribute, Action, Custom Condition, Integration, Timer — same as 7.6.

**Key addition in MAS:** Timer launch points and integration scripts can now replace custom Java cron tasks and Java Object Structure processing classes in SaaS-compatible ways.

**Automation Script Endpoints:** Scripts exposed as REST endpoints remain available in MAS.

**Best practice for SaaS clients:** All Java customisation requirements should be re-evaluated as automation script candidates before accepting that Java is required.

### Java Customisation (On-Premises Self-Managed Only — Not Available on IBM SaaS or IBM Managed)

Technically possible on self-managed OpenShift deployments, but the mechanism is fundamentally different from Maximo 7.6.

In MAS, Manage runs in containers. Adding Java customisations requires:
1. Creating custom container image layers that include the custom JAR files
2. Configuring Manage to use the custom images via the MAS operator configuration
3. Rebuilding and redeploying containers with each Manage update

IBM's strong guidance is to avoid Java customisation in MAS wherever possible. Automation Scripts cover the majority of use cases that previously required Java. Container-based Java customisation significantly complicates IBM support and the upgrade process.

For MAS 9.1 specifically: custom Java classes compiled against Java 8 or Java 11 must be recompiled for Java 17. This is a mandatory step for any client migrating from MAS 8.x or from Maximo 7.6 that carries Java customisations forward.

**In BRDs for MAS clients:** Java customisation should only be recommended as a last resort after exhausting configuration and automation script options. Flag any Java customisation requirement with a risk note and confirm the client understands the maintenance and upgrade burden.

---

## Reporting

- **BIRT 4.16** (MAS 9.1) — native operational reports. Parameterised, scheduled. Report Administration manages security and distribution.
- **Cognos Analytics 12** — advanced dashboards, natural language query assistant, integration with Jupyter Notebooks. Included with Manage.
- **KPI Manager / KPI Templates** — same as 7.6.
- **Operational Dashboard (RBA)** — Work Queue-based dashboard combining multiple result sets for a user persona. Replacement for Start Center (under active development).
- **Start Center** — still available. Result Set portlets, KPI portlets, Workflow Inbox, Quick Insert, Report List.
- **Cross-Suite Dashboards (MAS 9.1)** — unified views across Manage, Health, Monitor, Predict.

---

## Maximo Mobile — Comprehensive Reference

Maximo Mobile is the strategic mobile platform for MAS. It replaces Maximo Anywhere (which is not supported on MAS). It is a native application built on the **IBM Maximo Application Framework (MAF)**, using React.js for the UI layer.

### Architecture

```
iOS / Android / Windows Device
          ↓
Maximo Mobile Native App (React/MAF)
          ↓  (REST API over HTTPS)
Maximo Manage (OpenShift — Liberty containers)
          ↓
Database (Db2 / Oracle)
```

**Key architectural differences from Maximo Anywhere:**

| Characteristic | Maximo Anywhere (7.6) | Maximo Mobile (MAS) |
|---|---|---|
| Technology | Hybrid HTML5 / Worklight | Native React / MAF |
| Deployment | App store + MobileFirst Server (pre-7.6.4) or Maximo-hosted (7.6.4) | App store only |
| Configuration | Eclipse-based Anywhere Studio (app.xml) | MAF server-side configuration in Manage |
| Update delivery | New app version required from app store | Server-side configuration changes apply instantly |
| Offline model | Local cache downloaded before going offline | Selective offline sync |
| UI customisation | app.xml field additions | MAF configuration + Database Configuration |

**No separate mobile server is required.** Maximo Mobile connects directly to Maximo Manage via the published REST API. The same Manage environment serves both browser users and mobile users.

**App store distribution:** Maximo Mobile is downloaded from Apple App Store, Google Play Store, and Microsoft Store.

**Authentication:** Uses MAS identity provider (Azure AD, LDAP, OIDC). Single sign-on supported.

**Push Notifications:** Configured in Manage via the Push Notifications Administration application and the Notifications application (Integration module). Push notifications alert mobile users to new work order assignments, workflow tasks, and status changes. Requires MDM or device management configuration to enable push delivery.

**Work Zones:** Associate labor and crews with geographic zones in Manage. Used by Graphical Assignment (Maximo Scheduler/Dispatcher) for proximity-based work routing. Work Zones are visible in the mobile dispatching workflow.

### Offline Capability

Maximo Mobile supports offline working for field teams without network connectivity. The offline model is selective — only data relevant to the user is downloaded.

**How offline sync works:**
1. On login or sync, Manage pushes assigned work orders and related data to the device
2. The app stores this data locally in a structured cache
3. The user works against the local cache while offline — completing work, reporting actuals, adding materials, recording meter readings
4. On reconnection, the app pushes changes back to Manage via REST API
5. Conflicts are resolved using last-write-wins or configurable conflict resolution logic

**Offline data scope:** Work orders assigned to the current user, related job plan and task data, relevant asset and location data, storeroom item lists for material issue. Inspection forms are downloaded once at login (MAS 9.1 improvement — not re-downloaded per inspection).

### Maximo Mobile Applications — Detailed Reference

#### 1. Technician (Work Execution)
The primary field work execution application. Used by maintenance technicians, field engineers, and supporting staff.

**Core capabilities:**
- View list of work orders assigned to the current user (filtered by status, priority, due date)
- Review full work order details: description, asset, location, priority, dates, planned tasks
- Review planned labor, materials, tools, and services on the work order
- Start and stop work (changes work order status to INPRG)
- Report actual labor hours (craft, hours, start/finish time, labour type)
- Report actual material usage (issue items from storeroom, scan barcode to identify item)
- Report actual tool usage
- Add and edit work order log entries (work log, labour report)
- Record meter readings for the asset
- Report asset downtime (failure start, end, production impact)
- Complete failure reports (failure class, problem, cause, remedy)
- Create follow-up work orders
- Execute tasks in sequence with flow control (tasks must be completed in order)
- Review safety plan (hazards, precautions, lock-outs)
- Attach photos, documents, and voice recordings
- View asset and location work history
- Map view showing work order locations with turn-by-turn navigation
- Barcode and QR code scanning for assets, locations, and items
- Self-assign work from a work queue (MAS 9.1)
- Unassign and reassign work (MAS 9.1)
- View full asset work history in the field (MAS 9.1)

**Offline:** Full offline capability. Assigned work orders, tasks, planned data, and asset information downloaded to device.

#### 2. Work Approvals (Supervisor)
Used by supervisors and work planners to review and approve work orders on mobile.

**Core capabilities:**
- View list of work orders pending approval
- Review work order details: description, asset, location, planned costs, planned schedule, asset history
- Approve or reject work orders (with rejection reason)
- View work order status and progress
- Receive push notifications when a work order requires approval

**Offline:** Limited offline capability compared to Technician. Approval actions require connectivity to post status changes.

**Note:** Work Approvals has seen less active development than Technician since MAS 8.3. It is functional but not feature-complete as a full supervisor tool.

#### 3. Inspections
Used to execute structured inspection forms created in the Manage Inspection Forms work center.

**Core capabilities:**
- View list of active inspection work orders assigned to the user
- Open an inspection and navigate through question groups
- Record responses per question type:
  - Numeric values (with acceptable range validation)
  - Date and time values
  - Meter readings (linked to asset meters in Manage)
  - Single-choice list selections
  - Free text responses
  - Photo attachments (device camera)
  - Document attachments
- Voice-to-text for free text responses
- AI-assisted photo analysis via Maximo Visual Inspection (if licensed) — detects defects in photos captured during inspection
- Flag individual questions as requiring follow-up (generates a work order)
- Complete and submit the inspection
- Review previously completed inspections

**Inspection Form Architecture:** Forms are created in Manage (Manage Inspection Forms work center), published, and linked to Job Plans or PMs. When a PM generates a work order and the PM references a job plan with an inspection form, the Inspections app displays the form for that work order.

**MAS 9.1 improvement:** Inspection forms are downloaded once at login rather than per-inspection, improving performance for users with many inspection assignments.

**Offline:** Full offline capability. Forms and work order data downloaded to device.

#### 4. Service Requests (Mobile)
Used by any Maximo user to create and track service requests from a mobile device. Designed for non-technical users who need to report issues.

**Core capabilities:**
- Create a new service request with classification, description, location, and asset
- Attach photos and videos captured from device camera — particularly useful for documenting physical defects
- Use rich text formatting in description field
- View list of service requests created by the current user
- View current status and progress of submitted requests
- Add log notes to an open request
- Receive push notifications on request status changes

**Offline:** Can create service requests offline. Submitted when connectivity is restored.

#### 5. Asset Manager (RBA — Mobile)
Used for asset data collection, editing, and creation in the field.

**Core capabilities:**
- Search and view assets and their full details (specifications, meters, related records)
- Edit asset attributes and specifications
- Capture asset geospatial location via device GPS — records the asset's geographic coordinates
- Map view showing asset locations
- Create new asset records in the field
- Attach photos to asset records
- View asset work history

**Use case:** Useful during asset discovery exercises, commissioning new assets, and updating out-of-date asset registers in the field.

#### 6. Inventory Receiving (RBA — Mobile)
Two functions in one application covering material receipts and inter-storeroom transfers.

**Material Receipts (from Purchase Orders):**
- View list of Purchase Orders with pending receipts
- Select a PO and receive material line items
- Record received quantity, condition, and inspection status
- For rotating items: trigger serialisation — create individual asset records for each received unit
- Inspect items on receipt (record inspection status per line)
- Generate and print barcodes for received items
- Void receipt records for errors

**Shipment Receiving (inter-storeroom transfers):**
- View list of Inventory Usage documents in SHIPPED status (transferred from another storeroom)
- Receive items at the destination storeroom
- Record inspection status for received items
- Adjust balances in the destination storeroom on receipt
- Void receipt records if needed

**Offline:** Partial offline capability. Connected preferred for reconciliation steps.

#### 7. Inventory Counting (RBA — Mobile)
Used for physical inventory counting in storerooms.

**Core capabilities:**
- Select a Count Book (predefined set of items to count) or perform an ad hoc count
- Scan barcodes to identify items
- Record counted quantity for each item
- Compare counted quantity against system balance (expected)
- Identify and review variances
- Reconcile counts to adjust storeroom balances (online only — requires connectivity to post reconciliation)

**Three entry points:**
1. Count Books — structured, pre-defined count sets
2. Ad hoc count — select items manually for an unplanned count
3. Reconciliation — review and post previously recorded counts

**Offline:** Count recording is offline-capable. Reconciliation requires connectivity.

#### 8. Issues and Transfers (RBA — Mobile — Under Development in MAS 8.11/9.x)
Used for issuing inventory items from a storeroom.

**Core capabilities (current):**
- Issue items from a storeroom to a work order
- Process an existing Inventory Usage record or a reservation
- Create a new Inventory Usage record for an issue
- Barcode scanning to identify items

**Current limitations (as of MAS 9.x):** This application is still under active development. It does not yet fully replace the Manage Inventory Work Center. Staging, shipping workflow, and full returns capability are not yet complete. Monitor IBM release notes for progress.

**Offline:** Partial offline capability.

### Mobile Configuration Approach

**Adding a field to Maximo Mobile:**
1. If the field exists on the Manage object (e.g., WORKORDER) → it may already be configurable in MAF settings without any database changes
2. If the field does not exist → create it in Database Configuration first, then expose it via MAF configuration
3. MAF configuration changes apply server-side and take effect immediately on next device sync — no app store update required

**Configuring offline data download:**
The offline data downloaded to the device is controlled by queries configured in Manage. The query determines which work orders and related records are included in the device cache. This is configurable by the administrator and can be tuned based on field team size and data volume.

**Barcode and QR scanning:**
Native device camera used for scanning. Supported formats include Code 128, QR Code, Data Matrix. Configuration controls which fields trigger a scan (e.g., asset number, item number, inventory location).

**Push notifications setup:**
1. Configure the Notifications application in Manage (Integration module) — define notification events and recipients
2. Configure Push Notifications Administration — define push message content and delivery rules
3. Users must accept push notification permissions on their devices
4. MDM or device management policy may need to whitelist the Maximo Mobile app for push delivery

**MDM (Mobile Device Management) considerations:**
For enterprise deployments, integrate Maximo Mobile with an MDM platform (Microsoft Intune, Jamf for iOS). MDM handles app deployment, device enrolment, certificate trust, and security policy enforcement (e.g., enforce device PIN, remote wipe). This is an infrastructure requirement that should be documented in the BRD.

### Mobile Deployment Architecture Options

```
Option A — Direct (Standard)
Mobile Device → Internet / Enterprise Wi-Fi → Manage REST API (OpenShift Route/Ingress)

Option B — VPN
Mobile Device → VPN Tunnel → Internal Network → Manage REST API

Option C — API Gateway
Mobile Device → API Gateway (IBM DataPower, Azure APIM) → Manage REST API
```

For IBM SaaS, Option A is the standard. Only one VPN connection is allowed on IBM SaaS deployments. API Gateway is available for clients requiring additional security or traffic management.

**Bandwidth considerations:** Maximo Mobile is designed for intermittent and low-bandwidth connectivity. The offline-first approach reduces dependency on continuous connectivity. For remote field environments (mining, offshore, rural utilities), plan for large offline data packages downloaded in high-connectivity zones (site office, depot) before field deployment.

---

## Administration Applications Reference

| Application | Purpose |
|---|---|
| Database Configuration | Objects, attributes, domains, relationships, auditing, electronic signatures |
| Application Designer | Classic UI presentations, signature options, conditional UI |
| Automation Scripts | Business logic scripts and launch point management |
| Workflow Designer | Graphical workflow process design and revision |
| Workflow Administration | Monitor and manage active workflow instances |
| Escalations | Background monitoring and notification task configuration |
| Cron Task Setup | Manage scheduled background processes |
| Security Groups | Application, signature, and data access control |
| Users | Manage user-Security Group assignments within Manage |
| Organisations and Sites | Structural configuration, organisation and site options |
| Calendars | Working calendars, shifts, non-working periods |
| System Properties | Manage system-level configuration properties |
| Communication Templates | Email notification templates with bind variables |
| Classifications | Attribute hierarchy for assets, items, locations, work orders |
| Domains | Dropdown value list management |
| Actions | Reusable actions for workflow and escalation |
| Roles | Dynamic role resolution for workflow and communication |
| Migration Manager | Migrate configuration between environments |
| Conditional Expression Manager | Named conditions for conditional UI and workflow branching |
| KPI Manager / KPI Templates | KPI definition and grouping |
| Report Administration | BIRT report management, scheduling, security |
| Object Structures | Integration data schema definitions |
| Enterprise Services | Inbound integration service definitions |
| Publish Channels | Outbound integration channel definitions |
| External Systems | Define external systems for Integration Framework |
| Message Tracking | Monitor and reprocess integration messages |
| API Keys (RBA) | Manage REST API access keys |
| Push Notifications Administration | Configure mobile push notification delivery |
| Work Queue Manager | Define work queues for Operational Dashboard |
| Manage Inspection Forms (Work Center) | Create and publish inspection forms for Maximo Mobile |

---

## BRD-Specific Considerations for MAS 9.x Manage

### Establish Deployment Mode First
Self-managed, IBM Managed, or IBM SaaS? This determines which customisation methods are available and must be documented at the start of every BRD.

### AppPoint Analysis
Document: licenced AppPoints, user type breakdown (Limited/Base/Premium), projected AppPoint consumption after the proposed solution. Licensing implications must be identified at requirements stage.

### UI Paradigm Scope
Clarify for each functional area whether the requirement is for the Classic UI, an RBA application, or Maximo Mobile. This determines the configuration toolset.

### MAS 9.1 Java 17 Impact (for Migrations)
Document: volume of automation scripts and Java customisations, compatibility review requirement, recompilation and testing scope for Java 17.

### Mobile Scope
For any mobile requirement: confirm user population size, device types (iOS/Android/Windows), connectivity conditions (online-always vs offline-required), MDM platform in use, and whether push notifications are required. Each of these has architectural and security implications.

### Customisation Risk Flags
Flag any requirement that requires Java customisation on a SaaS or managed deployment. Flag any MAF UI customisation that exceeds standard MAF configuration capabilities.

### Migration from 7.6
If this is an upgrade engagement: Java customisation inventory, Anywhere-to-Mobile transition plan, integration redesign from SOAP/IIF to REST, BIRT report migration, Cognos migration, user authentication transition to MAS identity provider.
