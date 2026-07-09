/**
 * ArchitectureDiagram — SVG block diagram of the Connected Care Platform.
 * Renders natively in the browser, respects dark mode.
 */

export default function ArchitectureDiagram() {
  const isDark = document.body.classList.contains('awsui-dark');

  const bg = isDark ? '#0f1b2a' : '#ffffff';
  const border = isDark ? '#354150' : '#d5dbdb';
  const text = isDark ? '#e9ebed' : '#16191f';
  const textSub = isDark ? '#8d99a8' : '#5f6b7a';
  const orchBg = isDark ? '#1a3a5c' : '#e3f2fd';
  const orchBorder = isDark ? '#539fe5' : '#0972d3';
  const pmBg = isDark ? '#1a3c2a' : '#e8f5e9';
  const pmBorder = isDark ? '#29a329' : '#037f0c';
  const dmBg = isDark ? '#3a2a1a' : '#fff3e0';
  const dmBorder = isDark ? '#e07b00' : '#eb5f07';
  const peBg = isDark ? '#2a1a3a' : '#f3e5f5';
  const peBorder = isDark ? '#b07cc6' : '#7b2ea8';
  const infraBg = isDark ? '#1a2332' : '#f2f3f3';
  const infraBorder = isDark ? '#414d5c' : '#aab7b8';
  const arrow = isDark ? '#539fe5' : '#0972d3';
  const arrowLight = isDark ? '#414d5c' : '#aab7b8';

  return (
    <svg viewBox="0 0 1000 720" style={{ width: '100%', maxWidth: 1000, display: 'block', margin: '0 auto' }}>
      {/* Background */}
      <rect width="1000" height="720" fill={bg} rx="8" />

      {/* Title */}
      <text x="500" y="32" textAnchor="middle" fill={text} fontSize="18" fontWeight="700" fontFamily="sans-serif">
        Connected Care Platform — Architecture
      </text>

      {/* ===== USERS ===== */}
      <rect x="420" y="50" width="160" height="40" rx="6" fill={infraBg} stroke={infraBorder} strokeWidth="1.5" />
      <text x="500" y="75" textAnchor="middle" fill={text} fontSize="12" fontWeight="600" fontFamily="sans-serif">
        Clinicians / Engineers
      </text>

      {/* Arrow: Users → CloudFront */}
      <line x1="500" y1="90" x2="500" y2="115" stroke={arrow} strokeWidth="1.5" markerEnd="url(#arrowhead)" />

      {/* ===== FRONTEND ===== */}
      <rect x="350" y="115" width="300" height="45" rx="6" fill={infraBg} stroke={infraBorder} strokeWidth="1.5" />
      <text x="500" y="133" textAnchor="middle" fill={text} fontSize="11" fontWeight="600" fontFamily="sans-serif">
        CloudFront + S3
      </text>
      <text x="500" y="150" textAnchor="middle" fill={textSub} fontSize="10" fontFamily="sans-serif">
        React / Cloudscape UI — 5 Tabs
      </text>

      {/* Arrow: Frontend → WebSocket APIs */}
      <line x1="500" y1="160" x2="500" y2="185" stroke={arrow} strokeWidth="1.5" markerEnd="url(#arrowhead)" />

      {/* ===== WEBSOCKET API LAYER ===== */}
      <rect x="100" y="185" width="800" height="50" rx="6" fill="none" stroke={border} strokeWidth="1" strokeDasharray="4 2" />
      <text x="500" y="200" textAnchor="middle" fill={textSub} fontSize="10" fontFamily="sans-serif">
        WebSocket API Gateway (4 APIs — no timeout limits)
      </text>
      <rect x="120" y="210" width="160" height="20" rx="4" fill={orchBg} stroke={orchBorder} strokeWidth="1" />
      <text x="200" y="224" textAnchor="middle" fill={text} fontSize="9" fontFamily="sans-serif">Orchestrator WS</text>
      <rect x="310" y="210" width="160" height="20" rx="4" fill={pmBg} stroke={pmBorder} strokeWidth="1" />
      <text x="390" y="224" textAnchor="middle" fill={text} fontSize="9" fontFamily="sans-serif">Patient Monitoring WS</text>
      <rect x="500" y="210" width="160" height="20" rx="4" fill={dmBg} stroke={dmBorder} strokeWidth="1" />
      <text x="580" y="224" textAnchor="middle" fill={text} fontSize="9" fontFamily="sans-serif">Device Management WS</text>
      <rect x="690" y="210" width="160" height="20" rx="4" fill={peBg} stroke={peBorder} strokeWidth="1" />
      <text x="770" y="224" textAnchor="middle" fill={text} fontSize="9" fontFamily="sans-serif">Patient Engagement WS</text>

      {/* Arrows: WS → Agents */}
      <line x1="200" y1="230" x2="200" y2="270" stroke={orchBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />
      <line x1="390" y1="230" x2="390" y2="380" stroke={pmBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />
      <line x1="580" y1="230" x2="580" y2="380" stroke={dmBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />
      <line x1="770" y1="230" x2="770" y2="380" stroke={peBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />

      {/* ===== ORCHESTRATOR ===== */}
      <rect x="80" y="270" width="240" height="90" rx="8" fill={orchBg} stroke={orchBorder} strokeWidth="2" />
      <text x="200" y="290" textAnchor="middle" fill={text} fontSize="13" fontWeight="700" fontFamily="sans-serif">
        Orchestrator Agent
      </text>
      <text x="200" y="306" textAnchor="middle" fill={textSub} fontSize="9" fontFamily="sans-serif">
        5 Cross-Module Workflows
      </text>
      <text x="200" y="320" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">
        invoke_patient_monitoring
      </text>
      <text x="200" y="332" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">
        invoke_device_management
      </text>
      <text x="200" y="344" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">
        invoke_patient_engagement
      </text>
      <text x="200" y="356" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">
        execute_workflow / publish_workflow_event
      </text>

      {/* Dashed arrows: Orchestrator → Domain Agents */}
      <line x1="320" y1="310" x2="350" y2="400" stroke={orchBorder} strokeWidth="1.5" strokeDasharray="6 3" markerEnd="url(#arrowhead)" />
      <line x1="320" y1="330" x2="540" y2="400" stroke={orchBorder} strokeWidth="1.5" strokeDasharray="6 3" markerEnd="url(#arrowhead)" />
      <line x1="320" y1="350" x2="730" y2="400" stroke={orchBorder} strokeWidth="1.5" strokeDasharray="6 3" markerEnd="url(#arrowhead)" />

      {/* ===== DOMAIN AGENTS ===== */}
      {/* Patient Monitoring */}
      <rect x="340" y="380" width="180" height="100" rx="8" fill={pmBg} stroke={pmBorder} strokeWidth="2" />
      <text x="430" y="400" textAnchor="middle" fill={text} fontSize="12" fontWeight="700" fontFamily="sans-serif">
        Patient Monitoring
      </text>
      <text x="430" y="416" textAnchor="middle" fill={textSub} fontSize="9" fontFamily="sans-serif">8 Tools — WF-06</text>
      <text x="430" y="432" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Vitals, Trends, Deterioration</text>
      <text x="430" y="444" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Alert Thresholds, Clinical Events</text>
      <text x="430" y="460" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">5 Patients, 6 Vital Signs</text>

      {/* Device Management */}
      <rect x="540" y="380" width="180" height="100" rx="8" fill={dmBg} stroke={dmBorder} strokeWidth="2" />
      <text x="630" y="400" textAnchor="middle" fill={text} fontSize="12" fontWeight="700" fontFamily="sans-serif">
        Device Management
      </text>
      <text x="630" y="416" textAnchor="middle" fill={textSub} fontSize="9" fontFamily="sans-serif">15 Tools — WF-07</text>
      <text x="630" y="432" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Fleet Health, Telemetry, Diagnostics</text>
      <text x="630" y="444" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Assignments, Maintenance, Predictions</text>
      <text x="630" y="460" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">15 Devices, 5 Types, 11 Metrics</text>

      {/* Patient Engagement */}
      <rect x="740" y="380" width="180" height="100" rx="8" fill={peBg} stroke={peBorder} strokeWidth="2" />
      <text x="830" y="400" textAnchor="middle" fill={text} fontSize="12" fontWeight="700" fontFamily="sans-serif">
        Patient Engagement
      </text>
      <text x="830" y="416" textAnchor="middle" fill={textSub} fontSize="9" fontFamily="sans-serif">19 Tools — WF-08</text>
      <text x="830" y="432" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Medications, Appointments, Adherence</text>
      <text x="830" y="444" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">No-Show Risk, Notifications, Care Plans</text>
      <text x="830" y="460" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Drug Interactions, Discharge Plans</text>

      {/* ===== BEDROCK ===== */}
      <rect x="80" y="410" width="240" height="40" rx="6" fill={infraBg} stroke={infraBorder} strokeWidth="1.5" />
      <text x="200" y="435" textAnchor="middle" fill={text} fontSize="11" fontWeight="600" fontFamily="sans-serif">
        Amazon Bedrock (Claude) — Reasoning
      </text>
      {/* Arrows from agents to Bedrock */}
      <line x1="340" y1="430" x2="320" y2="430" stroke={arrowLight} strokeWidth="1" markerEnd="url(#arrowheadLight)" />
      <line x1="540" y1="430" x2="520" y2="430" stroke={arrowLight} strokeWidth="1" />
      <line x1="740" y1="430" x2="720" y2="430" stroke={arrowLight} strokeWidth="1" />
      <text x="520" y="425" textAnchor="middle" fill={textSub} fontSize="7" fontFamily="sans-serif">All agents use Bedrock</text>

      {/* ===== DATA LAYER ===== */}
      {/* Arrows: Agents → DynamoDB */}
      <line x1="430" y1="480" x2="430" y2="520" stroke={pmBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />
      <line x1="630" y1="480" x2="630" y2="520" stroke={dmBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />
      <line x1="830" y1="480" x2="830" y2="520" stroke={peBorder} strokeWidth="1.5" markerEnd="url(#arrowhead)" />

      <rect x="340" y="520" width="180" height="55" rx="6" fill={pmBg} stroke={pmBorder} strokeWidth="1" />
      <text x="430" y="538" textAnchor="middle" fill={text} fontSize="10" fontWeight="600" fontFamily="sans-serif">DynamoDB</text>
      <text x="430" y="552" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Patients, Vitals</text>
      <text x="430" y="564" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">2 Tables</text>

      <rect x="540" y="520" width="180" height="55" rx="6" fill={dmBg} stroke={dmBorder} strokeWidth="1" />
      <text x="630" y="538" textAnchor="middle" fill={text} fontSize="10" fontWeight="600" fontFamily="sans-serif">DynamoDB</text>
      <text x="630" y="552" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Devices, Telemetry, Assignments</text>
      <text x="630" y="564" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">4 Tables</text>

      <rect x="740" y="520" width="180" height="55" rx="6" fill={peBg} stroke={peBorder} strokeWidth="1" />
      <text x="830" y="538" textAnchor="middle" fill={text} fontSize="10" fontWeight="600" fontFamily="sans-serif">DynamoDB</text>
      <text x="830" y="552" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">Medications, Appointments, Adherence</text>
      <text x="830" y="564" textAnchor="middle" fill={textSub} fontSize="8" fontFamily="sans-serif">6 Tables</text>

      {/* ===== EVENTBRIDGE ===== */}
      <rect x="80" y="600" width="840" height="50" rx="8" fill={isDark ? '#1a2332' : '#fef3cd'} stroke={isDark ? '#e07b00' : '#eb5f07'} strokeWidth="1.5" />
      <text x="500" y="620" textAnchor="middle" fill={text} fontSize="12" fontWeight="700" fontFamily="sans-serif">
        Amazon EventBridge — connected-care-events
      </text>
      <text x="500" y="636" textAnchor="middle" fill={textSub} fontSize="9" fontFamily="sans-serif">
        8 Workflow Triggers — Cross-Module Event Routing — CloudWatch Logs (4 Log Groups)
      </text>

      {/* Arrows: Agents → EventBridge */}
      <line x1="430" y1="575" x2="430" y2="600" stroke={arrowLight} strokeWidth="1" markerEnd="url(#arrowheadLight)" />
      <line x1="630" y1="575" x2="630" y2="600" stroke={arrowLight} strokeWidth="1" markerEnd="url(#arrowheadLight)" />
      <line x1="830" y1="575" x2="830" y2="600" stroke={arrowLight} strokeWidth="1" markerEnd="url(#arrowheadLight)" />
      {/* EventBridge → Orchestrator (trigger) */}
      <line x1="200" y1="600" x2="200" y2="360" stroke={orchBorder} strokeWidth="1.5" strokeDasharray="6 3" markerEnd="url(#arrowhead)" />
      <text x="215" y="500" fill={orchBorder} fontSize="8" fontFamily="sans-serif" transform="rotate(-90, 215, 500)">
        Workflow Triggers
      </text>

      {/* ===== SIMULATORS ===== */}
      <rect x="80" y="670" width="840" height="35" rx="6" fill={infraBg} stroke={infraBorder} strokeWidth="1" />
      <text x="500" y="692" textAnchor="middle" fill={textSub} fontSize="10" fontFamily="sans-serif">
        Data Simulators: Vital Signs (60s) — Device Telemetry (60s) — Engagement Events (5m)
      </text>

      {/* Arrow defs */}
      <defs>
        <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={arrow} />
        </marker>
        <marker id="arrowheadLight" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
          <polygon points="0 0, 8 3, 0 6" fill={arrowLight} />
        </marker>
      </defs>
    </svg>
  );
}
