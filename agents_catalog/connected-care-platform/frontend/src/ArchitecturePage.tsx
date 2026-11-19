/**
 * Architecture Page — Complete technical overview of the Connected Care Platform.
 * Reflects the actual deployed architecture: AgentCore, Cognito IAM auth, Memory, KB.
 */

import Container from '@cloudscape-design/components/container';
import Header from '@cloudscape-design/components/header';
import SpaceBetween from '@cloudscape-design/components/space-between';
import Box from '@cloudscape-design/components/box';
import ColumnLayout from '@cloudscape-design/components/column-layout';
import ExpandableSection from '@cloudscape-design/components/expandable-section';

const S = ({ children, color }: { children: React.ReactNode; color?: string }) => (
  <Box variant="small" color={color as any}>{children}</Box>
);

const Tag = ({ label, color }: { label: string; color: string }) => (
  <span style={{
    display: 'inline-block', padding: '1px 8px', borderRadius: 4, fontSize: '0.8em',
    background: `${color}18`, color, border: `1px solid ${color}40`, marginRight: 4, marginBottom: 2,
  }}>{label}</span>
);

export default function ArchitecturePage() {
  return (
    <div style={{ overflowY: 'auto', height: 'calc(100vh - 200px)', padding: '0 4px' }}>
      <SpaceBetween size="l">

        {/* Platform Overview */}
        <Container header={<Header variant="h2">Connected Care Platform — Architecture</Header>}>
          <Box variant="p">
            Multi-agent AI healthcare platform built on Amazon Bedrock AgentCore. Five Strands agents — Patient Monitoring,
            Device Management, Patient Engagement, Inventory Management, and an Orchestrator — operate independently or collaborate through
            cross-module workflows. 49 tools, 13 DynamoDB tables, AgentCore Memory, and a Bedrock Knowledge Base
            with 37K clinical guidelines.
          </Box>
          <Box margin={{ top: 's' }}>
            <ColumnLayout columns={6}>
              <div style={{ textAlign: 'center' }}>
                <Box variant="h1" color="text-status-info">4</Box>
                <S>AgentCore Runtimes</S>
              </div>
              <div style={{ textAlign: 'center' }}>
                <Box variant="h1" color="text-status-success">49</Box>
                <S>Agent Tools</S>
              </div>
              <div style={{ textAlign: 'center' }}>
                <Box variant="h1" color="text-status-warning">5</Box>
                <S>Cross-Module Workflows</S>
              </div>
              <div style={{ textAlign: 'center' }}>
                <Box variant="h1">13</Box>
                <S>DynamoDB Tables</S>
              </div>
              <div style={{ textAlign: 'center' }}>
                <Box variant="h1" color="text-status-info">37K</Box>
                <S>Clinical Guidelines (KB)</S>
              </div>
              <div style={{ textAlign: 'center' }}>
                <Box variant="h1">5</Box>
                <S>CDK Stacks</S>
              </div>
            </ColumnLayout>
          </Box>
        </Container>

        {/* Architecture Diagram */}
        <Container header={<Header variant="h2">AWS Architecture Diagram</Header>}>
          <div style={{ textAlign: 'center', padding: '8px 0' }}>
            <img
              src="/architecture-diagram.png"
              alt="Connected Care Platform AWS Architecture"
              style={{ maxWidth: '100%', borderRadius: 8, border: '1px solid var(--color-border-divider-default, #d5dbdb)' }}
            />
          </div>
        </Container>

        {/* Request Flow */}
        <Container header={<Header variant="h2">Request Flow</Header>}>
          <Box variant="p" fontSize="body-m">
            <code style={{ fontSize: '0.9em', lineHeight: 2 }}>
              Browser → Cognito (JWT) → Identity Pool (temp IAM creds) → SigV4-signed request →
              Lambda Function URL (AWS_IAM auth) → AgentCore Runtime (Strands Agent) →
              Bedrock Claude Opus 4 → Tools (DynamoDB / EventBridge / KB) → Response
            </code>
          </Box>
        </Container>

        {/* Orchestrator */}
        <Container header={<Header variant="h2">Orchestrator Agent <Tag label="AgentCore Runtime" color="#0972d3" /></Header>}>
          <Box variant="p">
            Coordination layer — does not own data. Its tools are the domain agents. Detects cross-module queries,
            invokes agents in sequence, writes real-time execution traces to DynamoDB, and synthesizes unified clinical summaries.
          </Box>
          <ColumnLayout columns={2}>
            <div>
              <Box variant="h4">Tools (4)</Box>
              <ul style={{ margin: '4px 0', paddingLeft: 20, fontSize: '0.9em' }}>
                <li><code>invoke_patient_monitoring</code> — Sends prompts to PM agent via AgentCore invoke_agent_runtime</li>
                <li><code>invoke_device_management</code> — Sends prompts to DM agent via AgentCore invoke_agent_runtime</li>
                <li><code>invoke_patient_engagement</code> — Sends prompts to PE agent via AgentCore invoke_agent_runtime</li>
                <li><code>invoke_inventory_management</code> — Sends prompts to IM agent via AgentCore invoke_agent_runtime</li>
                <li><code>publish_workflow_event</code> — Publishes workflow events to EventBridge</li>
              </ul>
            </div>
            <div>
              <Box variant="h4">Cross-Module Workflows (5)</Box>
              <ul style={{ margin: '4px 0', paddingLeft: 20, fontSize: '0.9em' }}>
                <li><strong>WF-01</strong> Fall Detection & Root Cause Investigation</li>
                <li><strong>WF-02</strong> Medication-Device-Vitals Correlation</li>
                <li><strong>WF-03</strong> Patient Deterioration Cascade</li>
                <li><strong>WF-04</strong> Device Failure Patient Impact Assessment</li>
                <li><strong>WF-05</strong> Post-Discharge Remote Monitoring Activation</li>
              </ul>
            </div>
          </ColumnLayout>
          <Box margin={{ top: 'xs' }}>
            <Tag label="Strands Agents SDK" color="#0972d3" />
            <Tag label="Bedrock Claude Opus 4" color="#0972d3" />
            <Tag label="AgentCore Memory" color="#8b5cf6" />
            <Tag label="DynamoDB Traces" color="#eb5f07" />
            <Tag label="EventBridge" color="#e07b00" />
          </Box>
        </Container>

        {/* Domain Agents */}
        <ColumnLayout columns={4}>
          {/* Patient Monitoring */}
          <Container header={<Header variant="h3">Patient Monitoring <Tag label="8 tools" color="#10b981" /></Header>}>
            <Box variant="p" fontSize="body-s">
              Real-time vital sign monitoring for 5 patients. Trend analysis, deterioration prediction, clinical event publishing.
            </Box>
            <ExpandableSection headerText="Query Tools (4)" variant="footer">
              <S><code>get_patient_vitals</code> — Current vital signs from DynamoDB</S>
              <S><code>get_vital_sign_history</code> — Historical readings with time range</S>
              <S><code>list_patients</code> — All patients with risk levels</S>
              <S><code>get_patient_profile</code> — Demographics, conditions, room</S>
            </ExpandableSection>
            <ExpandableSection headerText="Analysis Tools (2)" variant="footer">
              <S><code>analyze_vital_trends</code> — Trend detection over configurable window</S>
              <S><code>get_alert_thresholds</code> — Per-patient alert thresholds</S>
            </ExpandableSection>
            <ExpandableSection headerText="Action Tools (2)" variant="footer">
              <S><code>update_alert_threshold</code> — Modify alert thresholds</S>
              <S><code>publish_clinical_event</code> — Publish to EventBridge</S>
            </ExpandableSection>
            <Box margin={{ top: 'xs' }}>
              <Tag label="DynamoDB: patients, vitals" color="#eb5f07" />
            </Box>
          </Container>

          {/* Device Management */}
          <Container header={<Header variant="h3">Device Management <Tag label="17 tools" color="#3b82f6" /></Header>}>
            <Box variant="p" fontSize="body-s">
              Fleet of 16 medical devices (5 types). Telemetry analysis, predictive maintenance, device-patient assignments, clinical guidelines KB.
            </Box>
            <ExpandableSection headerText="Query Tools (7)" variant="footer">
              <S><code>get_device_status</code> — Current device state</S>
              <S><code>get_device_history</code> — Historical status changes</S>
              <S><code>list_devices</code> — Full fleet inventory</S>
              <S><code>get_device_profile</code> — Model, serial, firmware, location</S>
              <S><code>get_devices_by_patient</code> — Devices assigned to a patient</S>
              <S><code>get_devices_by_type</code> — Filter by device type</S>
              <S><code>get_fleet_summary</code> — Fleet health overview</S>
            </ExpandableSection>
            <ExpandableSection headerText="Analysis Tools (4)" variant="footer">
              <S><code>analyze_device_telemetry</code> — Battery, calibration, thermal</S>
              <S><code>check_nearby_sensors</code> — Room-level device correlation</S>
              <S><code>get_maintenance_history</code> — Past work orders</S>
              <S><code>search_clinical_guidelines</code> — RAG search over 37K guidelines (Bedrock KB + S3 Vectors)</S>
            </ExpandableSection>
            <ExpandableSection headerText="Action Tools (6)" variant="footer">
              <S><code>assign_device_to_patient</code> — Create assignment</S>
              <S><code>unassign_device_from_patient</code> — Remove assignment</S>
              <S><code>update_device_status</code> — Change device state</S>
              <S><code>create_maintenance_work_order</code> — Schedule maintenance</S>
              <S><code>publish_device_event</code> — Publish to EventBridge</S>
            </ExpandableSection>
            <Box margin={{ top: 'xs' }}>
              <Tag label="DynamoDB: devices, telemetry, assignments, work_orders" color="#eb5f07" />
              <Tag label="Bedrock KB: 37K guidelines" color="#0972d3" />
              <Tag label="S3 Vectors" color="#3b82f6" />
            </Box>
          </Container>

          {/* Patient Engagement */}
          <Container header={<Header variant="h3">Patient Engagement <Tag label="20 tools" color="#f59e0b" /></Header>}>
            <Box variant="p" fontSize="body-s">
              Medications, appointments, care coordination, no-show risk, drug interactions, notifications, care plans.
            </Box>
            <ExpandableSection headerText="Query Tools (8)" variant="footer">
              <S><code>get_patient_engagement_profile</code> — Full profile with preferences</S>
              <S><code>get_medication_list</code> — Current medications</S>
              <S><code>get_medication_adherence</code> — Per-dose adherence records</S>
              <S><code>get_appointment_history</code> — Past appointments</S>
              <S><code>get_upcoming_appointments</code> — Scheduled appointments</S>
              <S><code>get_communication_log</code> — Notification history</S>
              <S><code>get_care_team</code> — Assigned care team members</S>
              <S><code>get_discharge_plan</code> — Discharge plan details</S>
            </ExpandableSection>
            <ExpandableSection headerText="Analysis Tools (4)" variant="footer">
              <S><code>assess_noshow_risk</code> — Appointment no-show prediction</S>
              <S><code>check_medication_adherence_pattern</code> — Per-medication adherence rates</S>
              <S><code>check_drug_interactions</code> — Known drug interaction check</S>
              <S><code>get_medication_change_history</code> — Medication change timeline</S>
            </ExpandableSection>
            <ExpandableSection headerText="Action Tools (8)" variant="footer">
              <S><code>schedule_appointment</code> — Create new appointment</S>
              <S><code>reschedule_appointment</code> — Change date/time</S>
              <S><code>cancel_appointment</code> — Cancel with reason</S>
              <S><code>send_notification</code> — Send via preferred channel</S>
              <S><code>update_communication_preferences</code> — Update contact prefs</S>
              <S><code>create_care_plan</code> — Create care plan</S>
              <S><code>publish_engagement_event</code> — Publish to EventBridge</S>
            </ExpandableSection>
            <Box margin={{ top: 'xs' }}>
              <Tag label="DynamoDB: profiles, medications, appointments, adherence, communications, care_plans" color="#eb5f07" />
            </Box>
          </Container>

          {/* Inventory Management */}
          <Container header={<Header variant="h3">Inventory Management <Tag label="9 tools" color="#ec4899" /></Header>}>
            <Box variant="p" fontSize="body-s">
              Floor-level supply tracking, stockout risk assessment, patient impact correlation, reorder management.
            </Box>
            <ExpandableSection headerText="Query Tools (4)" variant="footer">
              <S><code>get_floor_inventory</code> — Stock levels by floor</S>
              <S><code>get_item_status</code> — Detailed item status</S>
              <S><code>get_item_usage_history</code> — Dispensing/restock history</S>
              <S><code>get_supply_chain_status</code> — Pending orders and ETAs</S>
            </ExpandableSection>
            <ExpandableSection headerText="Analysis Tools (3)" variant="footer">
              <S><code>check_stockout_risk</code> — Predictive stockout assessment</S>
              <S><code>get_patients_affected_by_shortage</code> — Patient impact correlation</S>
              <S><code>get_substitute_items</code> — Alternative supply lookup</S>
            </ExpandableSection>
            <ExpandableSection headerText="Action Tools (2)" variant="footer">
              <S><code>create_reorder_request</code> — Trigger procurement</S>
              <S><code>publish_inventory_event</code> — Publish to EventBridge</S>
            </ExpandableSection>
            <Box margin={{ top: 'xs' }}>
              <Tag label="DynamoDB: inventory, inventory-transactions" color="#eb5f07" />
            </Box>
          </Container>
        </ColumnLayout>

        {/* AWS Services */}
        <Container header={<Header variant="h2">AWS Services</Header>}>
          <ColumnLayout columns={4}>
            <div>
              <Box variant="h4">Agent Infrastructure</Box>
              <S>Amazon Bedrock AgentCore Runtime (4 runtimes)</S>
              <S>Amazon Bedrock AgentCore Memory</S>
              <S>Amazon Bedrock AgentCore Observability</S>
              <S>Amazon Bedrock (Claude Opus 4)</S>
              <S>Amazon Bedrock Knowledge Base</S>
              <S>Strands Agents SDK (Python)</S>
            </div>
            <div>
              <Box variant="h4">Authentication</Box>
              <S>Amazon Cognito User Pool</S>
              <S>Amazon Cognito Identity Pool</S>
              <S>AWS IAM (SigV4 Function URL auth)</S>
              <S>Lambda Function URL (AWS_IAM)</S>
            </div>
            <div>
              <Box variant="h4">Data & Storage</Box>
              <S>Amazon DynamoDB (13 tables, PAY_PER_REQUEST)</S>
              <S>Amazon S3 (frontend hosting + guidelines)</S>
              <S>Amazon S3 Vectors (KB vector store)</S>
              <S>Amazon Titan Embeddings V2 (KB embeddings)</S>
            </div>
            <div>
              <Box variant="h4">Delivery & Events</Box>
              <S>Amazon CloudFront (frontend CDN)</S>
              <S>Amazon EventBridge (clinical events bus)</S>
              <S>Amazon CloudWatch (logs + observability)</S>
              <S>AWS CDK (TypeScript, 5 stacks)</S>
            </div>
          </ColumnLayout>
        </Container>

        {/* AgentCore Memory */}
        <Container header={<Header variant="h2">AgentCore Memory</Header>}>
          <Box variant="p">
            All four agents use AgentCore Memory for conversation continuity. Three long-term extraction strategies
            run asynchronously after each conversation.
          </Box>
          <ColumnLayout columns={3}>
            <div>
              <Box variant="h4">Short-Term Memory</Box>
              <S>Turn-by-turn conversation history within a session</S>
              <S>Enables follow-up questions: "What about their trends?"</S>
              <S>Stored per session_id + actor_id</S>
            </div>
            <div>
              <Box variant="h4">Long-Term Memory — 3 Strategies</Box>
              <S><strong>SessionSummarizer</strong> — Summarizes each conversation</S>
              <S><strong>ClinicianPreferences</strong> — Learns user preferences</S>
              <S><strong>ClinicalFacts</strong> — Extracts clinical facts about patients</S>
            </div>
            <div>
              <Box variant="h4">Memory Namespaces</Box>
              <S><code>/summaries/{'{actorId}'}/{'{sessionId}'}/</code></S>
              <S><code>/preferences/{'{actorId}'}/</code></S>
              <S><code>/facts/{'{actorId}'}/</code></S>
            </div>
          </ColumnLayout>
        </Container>

        {/* Knowledge Base */}
        <Container header={<Header variant="h2">Clinical Guidelines Knowledge Base</Header>}>
          <Box variant="p">
            37,000 clinical practice guidelines from 9 authoritative medical sources, indexed via Bedrock Knowledge Base
            with S3 Vectors. The Device Management agent queries this via the <code>search_clinical_guidelines</code> tool
            for procedure setup, troubleshooting, and treatment protocols.
          </Box>
          <ColumnLayout columns={3}>
            <div>
              <Box variant="h4">Data Sources</Box>
              <S>WHO — World Health Organization</S>
              <S>CDC — Centers for Disease Control</S>
              <S>NICE — National Institute for Health and Care Excellence (UK)</S>
              <S>PubMed / PubMed Central</S>
              <S>WikiDoc, CCO, CMA, ICRC, SPOR</S>
            </div>
            <div>
              <Box variant="h4">Coverage</Box>
              <S>Internal medicine, pediatrics, oncology</S>
              <S>Infectious disease, emergency care</S>
              <S>Device procedures, treatment protocols</S>
              <S>Drug guidelines, surgical procedures</S>
            </div>
            <div>
              <Box variant="h4">Technical Stack</Box>
              <S>Bedrock Knowledge Base (RAG)</S>
              <S>S3 Vectors (vector store)</S>
              <S>Titan Embeddings V2 (1024 dims, cosine)</S>
              <S>Source: EPFL/Meditron dataset (HuggingFace)</S>
            </div>
          </ColumnLayout>
        </Container>

        {/* Seed Data */}
        <Container header={<Header variant="h2">Seed Data</Header>}>
          <ColumnLayout columns={2}>
            <div>
              <Box variant="h4">5 Patients</Box>
              <table style={{ width: '100%', fontSize: '0.85em', borderCollapse: 'collapse' }}>
                <thead><tr>
                  <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid var(--color-border-divider-default, #d5dbdb)' }}>ID</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid var(--color-border-divider-default, #d5dbdb)' }}>Name</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid var(--color-border-divider-default, #d5dbdb)' }}>Room</th>
                  <th style={{ textAlign: 'left', padding: '4px 8px', borderBottom: '1px solid var(--color-border-divider-default, #d5dbdb)' }}>Risk</th>
                </tr></thead>
                <tbody>
                  <tr><td style={{ padding: '4px 8px' }}>P-10001</td><td style={{ padding: '4px 8px' }}>Margaret Chen</td><td style={{ padding: '4px 8px' }}>ICU-412</td><td style={{ padding: '4px 8px', color: '#ef4444' }}>CRITICAL</td></tr>
                  <tr><td style={{ padding: '4px 8px' }}>P-10002</td><td style={{ padding: '4px 8px' }}>James Rodriguez</td><td style={{ padding: '4px 8px' }}>Floor3-308</td><td style={{ padding: '4px 8px', color: '#f59e0b' }}>MODERATE</td></tr>
                  <tr><td style={{ padding: '4px 8px' }}>P-10003</td><td style={{ padding: '4px 8px' }}>Aisha Patel</td><td style={{ padding: '4px 8px' }}>Floor2-215</td><td style={{ padding: '4px 8px', color: '#f59e0b' }}>MODERATE</td></tr>
                  <tr><td style={{ padding: '4px 8px' }}>P-10004</td><td style={{ padding: '4px 8px' }}>Robert Kim</td><td style={{ padding: '4px 8px' }}>Floor1-102</td><td style={{ padding: '4px 8px', color: '#10b981' }}>LOW</td></tr>
                  <tr><td style={{ padding: '4px 8px' }}>P-10005</td><td style={{ padding: '4px 8px' }}>Lisa Okafor</td><td style={{ padding: '4px 8px' }}>Floor1-118</td><td style={{ padding: '4px 8px', color: '#f59e0b' }}>MODERATE</td></tr>
                </tbody>
              </table>
            </div>
            <div>
              <Box variant="h4">16 Devices (5 types)</Box>
              <S>Vital Signs Monitors — Philips MX800 (D-2001 to D-2004)</S>
              <S>Infusion Pumps — BD Alaris 8015 (D-3001 to D-3004)</S>
              <S>Ventilators — Hamilton C6, Draeger Evita (D-4001 to D-4003)</S>
              <S>Wearables — Biobeat BB-613 (D-5001 to D-5003)</S>
              <S>Smart Home — Withings BPM Connect, iHealth (D-6001 to D-6002)</S>
            </div>
          </ColumnLayout>
        </Container>

      </SpaceBetween>
    </div>
  );
}
