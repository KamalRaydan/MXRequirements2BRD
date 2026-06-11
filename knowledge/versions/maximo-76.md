# IBM Maximo 7.6.x Knowledge Base

## Overview

IBM Maximo 7.6.x is IBM's traditional Enterprise Asset Management (EAM) platform. It is a monolithic, Java EE-based application typically deployed on-premises or on virtual machines. It remains among the most widely deployed EAM platforms globally.

Maximo 7.6.1.3 (released July 2022) is the final fix pack. IBM ended standard support on 30 September 2025. Extended Support (1 year) and Sustained Support (up to 5 years) are available for clients on 7.6.1.3. Any BRD for a 7.6 client must address the end-of-support position and the planned migration path to IBM Maximo Application Suite (MAS).

---

## Version Family

| Version | Notes |
|---|---|
| 7.6.0.x | End of Support. No iFixes. |
| 7.6.1.0 | End of Support. No iFixes. |
| 7.6.1.1 | End of Support. No iFixes. |
| 7.6.1.2 | iFixes ended December 2023. |
| 7.6.1.3 | Last fix pack. Eligible for Extended/Sustained Support. |

New user licences removed from IBM catalogue: 19 April 2024. New users require trade-up to AppPoints (MAS licensing).

---

## Deployment Architecture

```
Browser / Maximo Everyplace / Anywhere / MAF Client
                    ↓
     IBM HTTP Server (Web Layer)
                    ↓
  WebSphere Application Server / WebLogic / Liberty
       (Java EE Application Server)
                    ↓
    Maximo Application (EAR deployment)
                    ↓
    Oracle / IBM DB2 / Microsoft SQL Server
```

Infrastructure teams need traditional Java EE skills: application server administration, JVM tuning, database DBA, LDAP integration. No Kubernetes or container knowledge required.

---

## Deployment Modes and SaaS vs On-Premises

Understanding the deployment mode is critical because it directly determines what customisation methods are available.

### On-Premises (Self-Managed)
The client manages all infrastructure and the Maximo application. Full customisation capability including Java class extensions, EAR rebuilds, database changes, and direct database access. This is the most common deployment for 7.6 clients.

### Customer-Hosted (Cloud Infrastructure, Client-Managed)
The client deploys Maximo on cloud VMs (AWS, Azure, IBM Cloud). Functionally equivalent to on-premises — same customisation capabilities.

### IBM Maximo SaaS (IBM-Managed)
IBM manages the infrastructure, application server, and Maximo application. This model has specific restrictions:

**Allowed on IBM SaaS:**
- Database Configuration (adding attributes, objects, relationships, domains)
- Application Designer (UI modifications, adding fields, signature options, conditional UI)
- Automation Scripts — Jython and JavaScript (the primary customisation mechanism)
- Workflow Designer
- Escalation configuration
- Integration Framework (Enterprise Services, Publish Channels via supported configuration)
- BIRT report development (with IBM providing a read-only replicated database on request)
- Classification and Domain management
- Security Group configuration

**Restricted or Not Supported on IBM SaaS:**
- Java MBO class extensions — no IBM SRE/product support; debugging is the client's responsibility
- Custom Java classes for cron tasks — not supported by IBM
- Custom action type "Custom Class" — not supported for troubleshooting
- Custom action type "Command Line Executable" — not supported
- Direct database access to production environment — not permitted
- Java class customisation of Object Structures for integration processing — no IBM support (automation scripts recommended instead)
- EAR file customisation or redeployment

**Practical implication for BRDs:** When the client is on IBM SaaS, every Java-based customisation requirement must be re-evaluated. In most cases an Automation Script equivalent can achieve the same result. Requirements that cannot be satisfied by scripting, configuration, or integration must be flagged as out-of-scope for the SaaS platform or escalated as exceptions.

---

## User Interface Paradigms

Maximo 7.6 has three coexisting UI types. A BRD should clarify which are in use and whether new functionality is expected in the Classic UI, Work Centers, or both.

### Classic Maximo UI
The traditional browser-based interface. All core Maximo applications (Work Order Tracking, Assets, Inventory, etc.) run in this interface. Configured using Application Designer. Compatible with all customisation methods. This is the primary UI for most 7.6 deployments.

### Work Centers
Modern, responsive browser UI introduced progressively from 7.6.0.5. Role-specific simplified experiences:
- **Work Supervisor Work Center** — manage open work, review service requests, assign labor, create follow-up work orders, monitor work progress to completion
- **Work Technician Work Center** — execute assigned work, report labor actuals, report failures, enter meter readings, create follow-up work orders
- **Manage Inventory Work Center** — storeroom management, review reservations, pick and stage items, issue and restock, physical count and reconciliation
- **Administration Work Center** — configure service request categories, data integration setup

Work Centers use a different UI technology from the Classic UI. They are not configurable via Application Designer. Card view and list view toggle available.

### Maximo Everyplace
A connected-only mobile solution included with Maximo 7.6 at no extra cost. Allows access to any licensed Maximo application through a mobile browser. Uses Maximo's existing Application Designer-configured presentations, adapted for smaller screens. No offline capability. Suitable for supervisors or approvers who need occasional mobile access and are always in connected environments.

---

## Core Functional Modules — Deep Reference

### Work Order Management

The central module for planning, executing, and tracking all maintenance work.

**Work Order Types:** Corrective maintenance, Preventive maintenance, Inspection, Modification, Safety, Emergency.

**Work Order Lifecycle (typical):** WAPPR (Waiting for Approval) → APPR (Approved) → WMATL (Waiting for Material) → WSCH (Waiting to be Scheduled) → INPRG (In Progress) → COMP (Complete) → CLOSE.

Status transitions are configurable. Additional custom statuses can be added via the WOSTATUS domain.

**Work Order Planning:**
- Labor plans (craft, skill level, planned hours, start/finish dates)
- Material plans (items from storeroom with reservations)
- Service plans (outside contractor services)
- Tool plans (tool items with hourly charge rates)
- Safety plans (automatically applied from job plan when linked)

**Job Plans:** Templates for work orders defining tasks, labor, materials, services, and tools. Applied manually or automatically from PM generation. Multi-level job plans supported (tasks referencing other job plans).

**Routes:** Define a set of assets and/or locations for recurring inspection or maintenance. Route stops can have individual job plans.

**Failure Reporting:** Four-level failure hierarchy (Failure Class → Problem → Cause → Remedy). Reported on work order completion. Drives reliability analysis and failure trending.

**Multi-Asset/Location:** A single work order can reference multiple assets and locations (e.g., all cooling tower assets in a single maintenance work order).

**Parent-Child Work Orders:** Hierarchical work order structures for complex maintenance projects.

**Key Maximo Objects:** WORKORDER, WOACTIVITY, WOSTATUS, WPLABOR, WPITEM, WPSERVICE, WPTOOL, WORELATE, LABTRANS, MATRECTRANS, TOOLTRANS, FAILUREREPORT, MULTIASSETLOCCI

### Asset Management

**Asset Register:** Each asset has a unique asset number, description, classification, serial number, vendor, manufacturer, and purchase/installation date. Assets exist within a Location hierarchy.

**Asset Hierarchy:** Assets can have parent-child relationships (e.g., Motor Pump Assembly > Motor > Bearing). Hierarchy supports cost rollup.

**Rotating Assets:** Assets linked to an Item in the Item Master. Tracked as individual serial-numbered units. Can move between locations and storerooms.

**Asset Lifecycle Tracking:** Purchase cost, installation date, warranty expiry, operating life, end-of-life date, salvage value.

**Specifications (Classifications):** Classification hierarchy applied to assets adds structured specification attributes (e.g., Motor Power: 55kW, Voltage: 415V). Enables asset querying by technical specification.

**Meters:** Continuous (e.g., running hours, odometer), Gauge (e.g., temperature, pressure), Characteristic (e.g., oil quality: Good/Fair/Poor). Meter readings trigger PM generation and condition monitoring alerts.

**Condition Monitoring:** Define measurement points with action limits. When a reading falls outside limits, a work order is automatically generated.

**Asset History:** Full history of work orders, meter readings, failure reports, moves, and cost transactions.

**Key Maximo Objects:** ASSET, ASSETSPEC, ASSETMETER, ASSETMNTSKD, METERREADING, LOCATION, LOCATIONSPEC, ASSETATRIBUTE

### Locations

**Location Types:** Operating (where assets are installed and work is performed), Storeroom (holds inventory), Labor (where labor is based), Repair Facility (where mobile assets go for maintenance).

**Location Hierarchy:** Systems → Functional Locations → Sub-locations. Defines the physical or functional breakdown of a facility.

**Service Addresses:** Postal addresses linked to locations. Used for map integration and geographic routing.

### Preventive Maintenance

**PM Records:** Define scheduled maintenance for an asset, location, or set of assets via a Route. A PM generates work orders based on frequency triggers.

**Frequency Types:**
- Time-based (e.g., every 30 days)
- Meter-based (e.g., every 500 running hours)
- Combined (time or meter, whichever comes first)
- Seasonal (specific months of the year)

**Sequences:** Different job plans applied based on the sequence of work order generation (e.g., quarterly inspection uses Job Plan A, annual inspection uses Job Plan B).

**Master PM:** Template for PMs linked to a rotating item type. Generates individual PM records for all assets/locations of that type. Changes to the Master PM can be propagated to all linked PMs.

**PM Forecasting:** Project future PM due dates for scheduling and resource planning.

**Key Maximo Objects:** PM, PMSEQ, PMFORECAST, PMANCESTOR

### Inventory Management

**Item Types:** Material items (physical stocked items), Service items (non-stocked services), Tool items (tools charged at hourly rates, can be rotating).

**Item Assembly Structure (IAS):** Parent-child item hierarchy applied to assets or locations to create a spare parts list.

**Storerooms:** Location records of type STOREROOM. Each storeroom holds inventory balances per item. Multiple storerooms per site supported.

**Inventory Records:** Item-storeroom combination with current balance, reorder point, reorder quantity, economic order quantity (EOQ), primary vendor, and bin location.

**Reservations:** When a work order plans a material item, a reservation is created reducing available stock. Reservations drive procurement if stock is insufficient.

**Inventory Transactions:** Issues (to work orders or direct charge), Returns (from work orders), Transfers (between storerooms), Adjustments (physical count corrections).

**Consignment Stock:** Vendor-owned inventory held in the client's storeroom. Charged on use.

**Condition Codes:** Material items can have multiple condition codes (e.g., New, Refurbished, Scrap) with different cost values.

**ABC Classification:** Classifies items by usage value (A=high, B=medium, C=low) for cycle counting prioritisation.

**Reorder:** Automatic reorder triggered when balance falls below reorder point. Generates Purchase Requisitions automatically via Inventory Reorder cron task.

**Key Maximo Objects:** ITEM, INVENTORY, INVUSE, INVUSELINESPLIT, MATRECTRANS, STORELOC, INVRESERVE, ITEMSTRUCT

### Purchasing and Procurement

**Purchase Requisition (PR):** Request for purchase of materials, services, or tools. Can be created manually, from a work order plan, from a storeroom reorder, or from a Desktop Requisition (self-service).

**Request for Quotation (RFQ):** Distribute PR lines to multiple vendors for competitive quoting. Compare quotations and award to one or multiple vendors. Converts to PO or Contract.

**Purchase Order (PO):** Formal purchase document with vendor. Can reference a contract for pricing. Supports centralised purchasing (one site orders, multiple sites receive). Revisions tracked with history.

**Receiving:** Match receipts to PO lines. Inspection workflow on receipt. Rotating items serialised on receipt and asset records created. Returns and void receipts supported.

**Invoices:** Three-way match (PO, Receipt, Invoice). Supports credit notes, debit notes, consignment invoices. Can reference multiple POs. Approval workflow via Workflow Designer.

**Internal PO:** Transfer items between organisations in the same Maximo instance. Inter-organisation pricing supported.

**Key Maximo Objects:** PR, PRLINE, PO, POLINE, POCOST, RFQ, RFQLINE, RFQBID, INVOICE, INVOICELINE, RECEIPT

### Contracts

**Contract Types:** Purchase (fixed price), Price (agreed rates), Blanket (release POs up to a value limit), Lease/Rental (asset lease with payment schedule), Labor Rate (agreed craft rates for outside labor), Warranty (time or meter-based, linked to assets/locations), Master (terms and conditions applied to multiple contracts), Service (maintenance of assets for fixed fee or payment schedule).

**Contract Lifecycle:** Draft → Pending Revision → Revised → Approved → Active → Expired.

**Key Maximo Objects:** CONTRACT, CONTRACTLINE, WARRANTYLINE, WOCONTRACT

### Labor and Resources

**Person Records:** Required for all Maximo users and any person referenced on records. Contains contact information, default site, work calendar.

**Labor Records:** Linked to a Person. Defines craft, skill level, internal and premium pay rates. Required for labor reporting on work orders.

**Crafts:** Define job types with skill levels (e.g., Electrician - Journeyman, Electrician - Master). Used in work planning and labor assignment.

**Qualifications:** Skills, certifications, and licences required for certain crafts. Expiry dates tracked. Used to validate labor assignment.

**Crews:** Groups of labor with defined craft positions. Created from Crew Types (templates). Assigned to work orders as a unit.

**Work Zones:** (Available in later 7.6.1.x versions) Geographic areas for routing work assignments to nearby labor.

**Key Maximo Objects:** PERSON, LABOR, CRAFT, LABORCRAFTRATE, QUALIFICATION, LABORQUAL, CREW, CREWTYPE

### Service Desk

**Ticket Classes:** Service Request, Incident, Problem. Activities are child records of tickets.

**Service Request (SR):** Raised by end users via self-service or by service desk agents. Classified, routed, and resolved. Work orders can be created from SRs.

**Incident:** Unplanned interruption to a service. Linked to assets, locations, and CIs. Can be escalated to a Problem.

**Problem:** Root cause investigation record. Solutions linked to Problems and applied to Incidents.

**Solutions:** Knowledge base of documented resolutions. Searchable by self-service users.

**Ticket Templates:** Predefined templates for common request types. Applied on ticket creation to pre-populate fields, classification, and activities.

**Service Level Agreements (SLAs):** Applied to ticket or work order types. Define commitments (contact time, response time, resolution time). Escalations monitor progress and notify as target times approach.

**Self-Service Portal:** End users create Service Requests and Desktop Requisitions without Maximo licences (if configured).

### Financial

**Chart of Accounts (GL Accounts):** Multi-segment GL code structure. Validated combinations. Carried on work orders, POs, invoices, and inventory transactions for cost posting.

**Cost Management:** Project-based cost tracking separate from GL. Work orders referenced to project tasks accumulate costs by project.

**Budget Reporting:** Budget lines against GL components, locations, or assets. Actual vs committed vs estimated variance reporting.

**Cost Rollup:** Asset hierarchy maintenance cost rollup (7.6.1.3+). Aggregates child asset costs to parent.

### Security and Access Control

**Security Groups:** Define access to sites, applications, signature options, and data. Users are assigned to multiple groups; permissions are additive.

**Application Access:** Each application is granted or denied per Security Group.

**Signature Options:** Named permissions within an application controlling access to specific actions (buttons, menu items, tabs, sections). Defined in Application Designer, granted in Security Groups. Common examples: SAVE, INSERT, DELETE, CHANGE STATUS, APPROVE, CLOSE.

**Data Restrictions:** Row-level security filtering records by attribute value (e.g., restrict a Security Group to see only work orders for their site).

**Attribute-Level Security:** Mark individual fields as read-only or hidden for specific Security Groups.

**Conditional UI:** Show or hide fields, tabs, and sections based on conditions evaluated at runtime. Conditions defined in Conditional Expression Manager.

**Authentication Options:**
- Native Maximo user store
- LDAP/Active Directory via WebSphere configuration
- SSO/SAML with additional configuration (on-premises)

### Workflow Engine

**Workflow Designer:** Graphical workflow tool. Defines multi-step routing, approvals, and notifications for any Maximo application.

**Workflow Components:**
- Task nodes — assign work to a person, person group, or role
- Condition nodes — branch the workflow based on attribute values
- Subprocess nodes — call another workflow
- Manual input nodes — request data entry from the assignee
- Interaction nodes — call external web services

**Workflow Features:**
- Auto-initiation on record creation or status change
- Workflow reassignment and delegation
- Escalation of overdue workflow assignments
- Communication Templates triggered by workflow actions
- Roles resolve to persons dynamically based on record data

**Escalations:** Independent background monitoring. Run on a defined schedule (cron-based). Detect conditions (e.g., work order priority 1 not assigned within 2 hours) and trigger actions or notifications without user involvement.

### Integration Module

**Integration Framework (IIF):**
- **Enterprise Services** — inbound data (external system sends data to Maximo)
- **Publish Channels** — outbound data (Maximo sends data to external system)
- **Object Structures** — define the data schema for integration messages. Can include related objects (e.g., Work Order + Labor Plans + Material Plans in one structure)
- **External Systems** — define the external system and map it to services and channels
- **End Points / Handlers** — define transport (HTTP, JMS, Web Service, File)
- **JMS Queuing** — asynchronous message processing
- **Message Tracking** — monitor and reprocess failed messages

**OSLC/REST APIs:** Create, read, update, delete operations on core objects. Supports JSON. Available for all MXAPIx resources. Used by Maximo Mobile and Anywhere as well as external integrations.

**Web Services:** SOAP/WSDL-based services generated from Object Structures.

**Automation Script REST Endpoints:** Expose Automation Scripts as lightweight REST endpoints without Java development.

**Launch in Context:** Open an external application from within Maximo, passing Maximo record data as URL parameters.

---

## Making Changes — Configuration and Customisation Reference

### Database Configuration

The Database Configuration application modifies the Maximo application data model. Changes are stored in the Maximo database metadata and applied to the underlying database via "Apply Configuration Changes" (also called "Configure Database").

**Adding an Attribute (Field) to an Existing Object:**
1. Open Database Configuration, find the object (e.g., WORKORDER)
2. Add a new attribute row: name, data type (ALN, UPPER, INTEGER, DECIMAL, DATE, DATETIME, YORN, BLOB), length, required, default value
3. Set a Domain if applicable (restricts values to a list via ALNDOMAIN or NUMERICDOMAIN)
4. Set a class name (Java field class) if custom validation logic is attached
5. Run Apply Configuration Changes → generates and executes the ALTER TABLE DDL
6. Add the attribute to the relevant Application Designer presentation to make it visible

**Adding a New Object (Table):**
1. Create the object in Database Configuration with its attributes
2. Define the parent object if it is a child (e.g., a new child of WORKORDER)
3. Define the relationship between parent and child
4. Run Apply Configuration Changes
5. Create a new application in Application Designer or add a table window to an existing application

**Relationships:**
Define JOIN relationships between objects using SQL WHERE clauses. Used by Application Designer to display related data in Table Windows and by Object Structures for integration.

**Domains:**
Value lists that populate dropdown fields. Types: ALN (text list), NUMERIC, SYNONYM (maps internal values to display values), CROSSOVER (copies values between fields), TABLE (look-up from another object), NUMERICRANGE.

**Audit Trails:**
Enable auditing on any object or attribute. Maximo records before/after values, user, and timestamp for every change. Audit data stored in a separate audit table (e.g., WORKORDER → WORKORDERAUDIT).

**Electronic Signatures:**
Configure fields to require electronic signature (re-authentication) before a value change is saved. Used for regulatory compliance (FDA, ISO).

**Indexes:**
Add database indexes to improve query performance on frequently searched attributes.

**Maxvars:**
System-level configuration variables stored in the MAXVARS table. Control system-wide behaviour (e.g., default work order status, numbering sequences).

### Application Designer

Application Designer modifies the user interface of Classic Maximo applications. It does not modify the database schema — that is done in Database Configuration.

**What Application Designer Controls:**
- Field visibility, labels, required status, read-only status
- Tab layout and tab visibility
- Section layout within tabs
- Table window configuration (columns, ordering, filtering)
- Toolbar buttons and their actions
- Menu actions (Action menu items)
- Signature Option definitions (the permission name, not the grant — that is done in Security Groups)
- Conditional properties (show/hide/required based on conditions)
- Application-level help text
- New application creation (from scratch or cloned from existing)

**How to Modify a Presentation:**
1. Open Application Designer, find the application
2. Switch to Design mode
3. Drag fields from the Field Search panel onto the presentation
4. Adjust properties: label, required, read-only, hidden, event handlers
5. Add signature options to control access to actions
6. Save (changes go live immediately — no server restart required)

**Signature Options:** Created in Application Designer, granted in Security Groups. A Sig Option definition includes the option name and description. Granting it in a Security Group gives users in that group the ability to perform that action. Revoking it prevents access even if the UI element is visible.

**Conditional UI:**
Use the Conditional Expression Manager to define named conditions (SQL-like expressions). Apply conditions to fields, sections, and tabs in Application Designer to control visibility or required status based on field values, user attributes, or security group membership.

**Export/Import XML:**
Presentations can be exported as XML files. Useful for version control and migration between environments (Dev → Test → Production). On IBM SaaS, this is the recommended approach for tracking Application Designer changes.

**Cloning Applications:** Copy an existing application and customise it. Allows creation of role-specific views without modifying the base application.

**Note:** Application Designer applies to Classic UI only. Work Centers and Role Based Applications (RBA/MAF) cannot be configured through Application Designer.

### Automation Scripts

Automation Scripts extend Maximo business logic without requiring Java compilation or server restarts. Code is stored in the Maximo database and executed at runtime by the scripting framework. Changes take effect immediately after saving.

**Supported Languages:** Jython (Python-syntax, most common), JavaScript/Nashorn (7.6.1+), and any other JSR223-compliant scripting engine on the classpath.

**Launch Point Types:**

| Launch Point Type | When It Fires |
|---|---|
| Object launch point | On object events: initialize, add, beforeSave, afterSave, beforeDelete, afterDelete, allowSave, canDelete |
| Attribute launch point | When a specific field value changes (on field exit) |
| Action launch point | Called explicitly from Workflow, Escalation, or a UI button/menu action |
| Custom condition | Returns true/false, used in Workflow, Security, and Conditional UI |
| Integration | Fires during Integration Framework processing (inbound/outbound object structure processing) |
| Timer launch point | Fires on a schedule (similar to a cron task) |

**What Automation Scripts Can Do:**
- Read and modify fields on the current record (MBO)
- Create new records in any Maximo application object
- Query and navigate related records via relationships
- Change record status
- Throw validation errors or warnings
- Invoke other automation scripts
- Call REST APIs (HTTP calls using Java URL/HttpClient libraries)
- Call Integration Framework services
- Access system services (mxServer, UserInfo, MaximoDD)
- Log to the Maximo log file
- Read system properties (MAXVARS, PROPERTIES)

**Common Automation Script Patterns:**
- Default a field value on record creation
- Validate a field value against business rules
- Populate fields on a child record when a parent is saved
- Auto-generate a related record (e.g., create a follow-up work order on close)
- Send an HTTP request to an external system on a status change
- Apply conditional logic that would otherwise require Java

**Integration Script Example Use:** Replace Java processing classes on Enterprise Services or Publish Channels for transformation and routing logic.

### Java Customisation (On-Premises Only — Not Available on IBM SaaS)

Java customisation directly extends the Maximo server-side business object framework. It requires compiling Java classes, adding them to the Maximo classpath, rebuilding the EAR file, and redeploying to the application server. A server restart is required for changes to take effect.

**MBO (Managed Business Object) Extensions:**
Each Maximo object (WORKORDER, ASSET, PO, etc.) has a corresponding Java MBO class. To extend behaviour, create a subclass that overrides specific methods:
- `initialize()` — set default field values
- `validate()` — validate fields before save
- `save()` — pre or post save logic
- `canDelete()` — control deletion
- `add()` — on record creation

The subclass is registered in Database Configuration under the object's class name attribute.

**Field Class Extensions:**
Individual attributes can have a Java field class that fires on field-level events (initValue, validate, action). Used for complex field-level defaults or cross-field validations that are tightly coupled to UI interaction.

**Data Bean Extensions:**
Java classes that support UI interactions not handled at the MBO layer. Less commonly used but support complex UI event handling.

**Custom Applications:**
New Maximo applications can be created entirely in Java (extending base Maximo application beans) combined with an Application Designer presentation. The Java class handles server-side logic; Application Designer handles the UI.

**Custom Cron Tasks:**
Java class implementing the CronTaskInstance interface, registered in Cron Task Setup. Runs background processes on a schedule.

**Custom Web Services:**
Java servlets or JAX-WS endpoints deployed as part of the Maximo EAR. Used for custom API endpoints not available via the standard Integration Framework.

**Upgrade Risk:** Every Java customisation file must be reviewed and recompiled for every Maximo fix pack, major version, or MAS migration. Heavy Java customisation is the single largest driver of upgrade cost and risk. BRDs should document all Java customisations and flag them as upgrade liabilities.

---

## Reporting

- **BIRT** — native report development tool. Eclipse-based IDE. Parameterised operational reports. Scheduled distribution via email. Report Administration application manages report security and scheduling.
- **Cognos Analytics** — available from 7.6.1.2+ via integration. Advanced dashboards, ad-hoc query, multi-dimensional analysis.
- **KPIs** — query-driven single numeric values with green/amber/red thresholds. Displayed on Start Center portlets. KPI Manager and KPI Templates for management.
- **Start Center Result Sets** — configurable query-based lists displayed as portlets. Not proper reports but frequently used for operational dashboards.
- **QBE (Query by Example)** — built-in ad hoc filtering within every Maximo application list. Not a reporting tool but commonly used by power users.

---

## Mobile Solutions for Maximo 7.6

Maximo 7.6 has three mobile options. They vary significantly in capability, architecture, and offline support.

### 1. Maximo Everyplace (Connected Only — Included)
Browser-based mobile access to any licensed Maximo application. No app installation. Uses Application Designer-configured presentations adapted for mobile screens. No offline capability. Suitable for supervisors or approvers who occasionally need mobile access in connected environments (office, control room, Wi-Fi area).

No separate licence required. Configuration is done in Application Designer by adjusting presentation sizes for mobile viewports.

### 2. Maximo Anywhere (Disconnected Capable — Separately Licensed)

The primary purpose-built mobile platform for Maximo 7.6. Native apps for iOS and Android (and Windows). Supports offline/disconnected operation through a local data cache on the device. Syncs with Maximo when connectivity is available.

**Architecture (Anywhere 7.6.4):**
In 7.6.4 (the latest version), IBM removed the dependency on IBM MobileFirst Server. All Anywhere components are hosted within the Maximo application server itself. Anywhere apps communicate directly with the Maximo REST APIs. The Anywhere Administration application (within Maximo) manages deployments and rollback.

Previous versions (7.6.3 and earlier) required a separate IBM MobileFirst Server (formerly IBM Worklight) as middleware between the mobile app and Maximo.

**Configuration:** Anywhere apps are configured via the Anywhere Studio — an Eclipse-based IDE with Anywhere-specific plugins. The app definition (app.xml) controls which fields appear, their layout, download queries, and available actions. The app.xml is portable between Anywhere versions.

**The Nine Maximo Anywhere Applications:**

| Anywhere App Name (7.6.4) | Previous Name (7.6.3) | Description |
|---|---|---|
| IBM Maximo Technician | IBM Maximo Work Execution | Primary field work execution. View assigned work orders, review task details, report labor actuals, record material and tool usage, maintain work log, report failures, report downtime, enter meter readings, create follow-up work orders. Map view with directions. Barcode scanning. Voice recognition. Flow control for sequential tasks. |
| IBM Maximo Supervisor | IBM Maximo Work Approval | Work order approval for supervisors, planners, and financial approvers. Review planned costs, schedules, and asset history. Approve or reject work orders. Report downtime on multi-asset work orders. |
| IBM Maximo Inspector | IBM Maximo Inspection | Execute inspection forms linked to work orders. Navigate measurement points along a route. Record gauge and characteristic readings. Trigger work orders based on readings. |
| IBM Maximo Asset Manager | IBM Maximo Asset Data Manager | View and edit asset records in the field. Record meter readings. View work history. Add or update asset attributes and specifications. |
| IBM Maximo Asset Auditor | IBM Maximo Asset Audit | Perform physical asset audits in a set of locations. Verify assets are present, scan barcodes/RFID to confirm. Add new assets discovered in the field. Mark assets as audited or missing. |
| IBM Maximo Service Requestor | IBM Maximo Service Request | Create service requests from the field. Select classification, describe the issue, attach photos. View status of previously submitted requests. |
| IBM Maximo Issues Returns | IBM Maximo Issues and Returns | Issue items from a storeroom to a work order. Return unused items to a storeroom. Scan barcodes to identify items. View reservations. |
| IBM Maximo Transfers Receipts | IBM Maximo Transfers-Receiving | Create and process inter-storeroom transfer records (Inventory Usage). Receive transferred items at the destination storeroom. Receive purchased items from POs. Inspect received items. Void receipt records. |
| IBM Maximo Cycle Counts | IBM Maximo Physical Count | Perform physical inventory counts. Select a storeroom and count items. Supports counted versus expected balance comparison. Reconcile counts to adjust storeroom balances. Barcode scanning to identify items. |

**Industry Solution Anywhere Extensions:**
- **Work Execution with Calibration** — extended version of Work Execution for calibration work orders. Record as-found and as-left measurements against data sheet templates.
- **Operator Rounds (Nuclear)** — nuclear-specific rounds and operator data collection.
- **E-Flight Log Book (ACM/Aviation)** — flight log recording for Maximo Aviation clients.
- **Incident Reporter (HSE/Oil and Gas)** — incident reporting for Health, Safety, and Environment engagements.

**Offline Capability:** Anywhere downloads a data cache to the device before going offline. Download queries define which records are available offline (e.g., work orders assigned to me due in the next 7 days). Users work against the local cache; data is synchronised to Maximo on reconnection.

**Customisation:** Via Anywhere Studio (Eclipse IDE with Anywhere plugins). Consultants can add fields to the app.xml, modify layout, change download queries, and add custom actions. RFID and barcode scanning supported natively.

**Note:** Maximo Anywhere is not supported on MAS. Maximo Mobile (the MAS mobile solution) replaces Anywhere.

### 3. Maximo Application Framework (MAF) Work Centers (Connected)
The Work Centers described earlier (Work Supervisor, Work Technician, Manage Inventory, Administration) are built on MAF — a precursor to the MAS mobile UI framework. They are browser-based and connected-only. They represent IBM's transitional step between the Classic UI and the fully native MAS Maximo Mobile platform.

---

## Industry Solutions and Add-ons (7.6)

| Add-on | Scope |
|---|---|
| Maximo Scheduler | Graphical scheduling (long/medium/short term), graphical assignment, repair facility scheduling |
| Maximo Spatial / GIS | Map-based asset and work management via ESRI ArcGIS. Spatial queries, geographic routing |
| Maximo HSE | Health, Safety, Environment — permits to work, hazard identification, incident management |
| Maximo Linear Assets | Linear infrastructure management (pipelines, roads, rail, utilities) with chainage-based positioning |
| Maximo Oil and Gas | Oil and gas industry-specific extensions |
| Maximo Nuclear | Nuclear power industry-specific extensions including Operator Rounds |
| Maximo Transportation | Fleet management, vehicle maintenance, fuel tracking |
| Maximo Aviation (ACM) | Aviation MRO — airworthiness, component tracking, flight log books |
| Maximo Calibration | Measurement and test equipment calibration management with data sheets |
| Maximo Inventory Optimisation | Storeroom replenishment optimisation |

Confirm which add-ons the client holds licences for before designing any solution that depends on them.

---

## Administration Applications Reference

| Application | Purpose |
|---|---|
| Database Configuration | Manage objects, attributes, relationships, domains, auditing, electronic signatures |
| Application Designer | Configure UI presentations, signature options, conditional properties |
| Automation Scripts | Create and manage scripts and their launch points |
| Workflow Designer | Build and revise workflow process diagrams |
| Workflow Administration | Monitor and manage active workflow instances |
| Escalation Configuration | Define and manage background monitoring and notification tasks |
| Cron Task Setup | Manage scheduled background processes |
| Security Groups | Define application, signature, and data access |
| Users | Manage user-Security Group assignments |
| Organisations and Sites | Define organisational structure, site options, system defaults |
| Calendars | Define working calendars, shifts, non-working periods |
| System Properties | Manage MAXIMO system-level configuration properties |
| Communication Templates | Define email templates with bind variables |
| Classifications | Define attribute hierarchies for assets, items, locations, work orders |
| Domains | Manage dropdown value lists |
| Actions | Define reusable actions for workflow and escalation |
| Roles | Define dynamic role resolution for workflow and communication templates |
| Migration Manager | Migrate configuration and reference data between environments |
| Conditional Expression Manager | Define named conditions for conditional UI and workflow branching |
| KPI Manager | Define and manage KPIs displayed on Start Centers |
| Report Administration | Manage BIRT reports, scheduling, security |
| Anywhere Administration | (7.6.4+) Manage Anywhere app deployments and rollbacks |
| External Systems | Define external systems for Integration Framework |
| Object Structures | Define integration data schemas |
| Enterprise Services | Define inbound integration services |
| Publish Channels | Define outbound integration channels |
| Message Tracking | Monitor integration message processing |

---

## BRD-Specific Considerations for Maximo 7.6

### End of Support Position (Mandatory)
Document: exact version, Extended/Sustained Support status, migration roadmap to MAS.

### Deployment Mode
Document: on-premises, customer-hosted, or IBM SaaS. This determines which customisation methods are available.

### Customisation Inventory
For existing implementations: Java MBO extensions, custom applications, automation scripts, custom reports, integration connections. Directly determines migration cost.

### Upgrade Risk Flags
Any requirement satisfied by Java customisation, database triggers, or custom EAR deployments should be explicitly flagged with an upgrade risk note in the BRD.

### Add-on Licence Confirmation
Confirm licenced add-ons before designing solutions that depend on Scheduler, Spatial, HSE, Calibration, etc.

### Mobile Strategy
Any mobile requirement should prompt discussion of: current mobile solution in use, device population, offline requirements, and whether this is a driver for migration to MAS and Maximo Mobile.
