# Connected Care Platform — PR/FAQ

## Press Release

**Connected Care Platform Transforms Hospital Operations and Medical Device Management with Multi-Agent AI**

Today we announce the Connected Care Platform, a multi-agent AI system built on Amazon Bedrock AgentCore that unifies patient monitoring, medical device management, hospital supply chain, and care coordination through a single conversational interface. The platform serves two audiences from the same data layer: hospital clinical staff who manage patient care, and medical device manufacturers who manage their installed base across hospital customers.

The platform deploys 7 AI agents — Patient Monitoring, Device Management, Patient Engagement, Inventory Management, Field Service Intelligence, Account Intelligence, and an Orchestrator — that operate independently or collaborate through 18 cross-agent workflows. Clinicians ask natural language questions and receive correlated insights that would normally require checking multiple systems: "Patient P-10001 is deteriorating — is it a medication reaction or a device malfunction?" The orchestrator coordinates across agents to deliver a unified clinical picture.

For hospital staff, the platform introduces AgentCore Memory for long-term patient context. Clinical observations recorded by one nurse are available to the next clinician in a subsequent shift or session, creating continuity of care that survives browser refreshes and shift handoffs. A PHI access control layer ensures only care team members can access patient data, with identity verification enforced at the proxy level before any agent is invoked.

For medical device companies, the same device telemetry that hospitals generate becomes a revenue and operations layer. The Field Service agent predicts device failures across the installed base and plans FSE dispatches. The Account Intelligence agent scores customer health and flags contract renewal risks. A Device Digital Twin provides a full lifecycle view per device — predictive maintenance countdown, peer comparison across hospital sites, firmware journey, and service history. Three new workflows address regulatory recall response, proactive contract renewal packaging, and competitive intelligence detection.

The platform runs entirely on AWS — AgentCore for agent runtimes, DynamoDB for the data layer, EventBridge for event-driven workflows, Cognito for authentication, CloudFront for the frontend, and Bedrock Claude models for reasoning. All agents are built with the Strands SDK.

"We built this to show that the same connected device data can serve both the hospital and the manufacturer," said the development team. "The clinician gets a patient-aware assistant. The device company gets an installed base intelligence platform. Neither needs a new dashboard — they just ask questions."

## Frequently Asked Questions

**Q: What problem does this solve for hospitals?**
Clinicians currently check 4-5 separate systems to get a complete picture of a patient — vitals in one system, medications in another, device status in a third, supply levels in a fourth. The Connected Care Platform correlates all of these through a single conversational interface. A charge nurse starting a shift can ask for a floor briefing and get patients, devices, supplies, and staffing in one response.

**Q: What problem does this solve for medical device companies?**
Device manufacturers have limited visibility into how their devices perform across hospital customers. Service is reactive, contract renewals are based on gut feel, and regulatory compliance is manual. This platform gives them fleet-wide telemetry analysis, predictive service dispatch, account health scoring, and automated post-market surveillance — all from data the hospitals already generate by using the devices.

**Q: How does the PHI access control work?**
Every request that mentions a patient ID is checked against a care team table before any agent is invoked. If the user's email is not on the patient's care team, the request is blocked at the proxy level — the agent never sees the data. Users can join a care team through an identity verification flow in the UI. On discharge, patient memory is cleared from both DynamoDB and AgentCore Memory.

**Q: What is AgentCore Memory and why does it matter?**
AgentCore Memory provides long-term semantic storage for patient observations. When a nurse records "patient became dizzy after Furosemide increase, BP dropped to 82/55," that observation persists across sessions. A different clinician in a later shift can ask "how did this patient respond to medication changes?" and get the full history — even though they never had that conversation. This creates continuity of care that traditional EHR notes don't provide.

**Q: What is the Device Digital Twin?**
A full-page lifecycle view for any device in the installed base. It shows the device identity, a predictive maintenance countdown (days until service needed), telemetry sparkline charts with auto-refresh, a peer comparison bar chart against the same model at other hospitals, a firmware journey visualization, and a service history timeline. Device IDs in chat responses are clickable links that open the twin.

**Q: How many workflows are there?**
18 workflows across two personas. 15 clinical workflows for hospital staff (fall investigation, deterioration cascade, supply shortage impact, shift handoff briefings, patient admission/discharge with memory, etc.) and 6 MedTech workflows for device manufacturers (proactive service dispatch, post-market surveillance, account health review, regulatory recall response, contract renewal packaging, competitive intelligence).

**Q: What AWS services does it use?**
Amazon Bedrock AgentCore (agent runtimes and memory), Amazon Bedrock (Claude Opus and Sonnet models), Amazon DynamoDB (15 tables), Amazon EventBridge (event-driven workflows), Amazon Cognito (authentication), Amazon CloudFront and S3 (frontend), AWS Lambda (proxy), AWS App Runner (Nova Sonic voice), and a Bedrock Knowledge Base with 37K clinical guidelines.

**Q: Can the platform be extended?**
Yes. The agent architecture is modular — new agents can be added without modifying existing ones. The orchestrator automatically routes to new agents based on system prompt updates. New workflows are defined as step sequences in Python and registered in the workflow registry. The frontend dynamically renders workflow cards from the workflow definitions.

**Q: How does the persona-based UI work?**
After login, users select their role — Hospital Staff or MedTech Operations. The sidebar, available agents, and workflow page filter based on the selected persona. Hospital Staff sees clinical agents and clinical workflows. MedTech Operations sees Field Service, Account Intelligence, and MedTech workflows. The Orchestrator is available to both. Users can switch roles without signing out.
