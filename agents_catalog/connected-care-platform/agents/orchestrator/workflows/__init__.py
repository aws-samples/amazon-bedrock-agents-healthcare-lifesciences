"""Workflow registry — maps trigger events to workflow definitions."""

from .wf01_fall_investigation import WF01_FALL_INVESTIGATION
from .wf02_medication_correlation import WF02_MEDICATION_CORRELATION
from .wf03_deterioration_cascade import WF03_DETERIORATION_CASCADE
from .wf04_device_failure_impact import WF04_DEVICE_FAILURE_IMPACT
from .wf05_post_discharge_monitoring import WF05_POST_DISCHARGE_MONITORING
from .wf06_critical_shortage_impact import WF06_CRITICAL_SHORTAGE_IMPACT
from .wf07_admission_readiness import WF07_ADMISSION_READINESS
from .wf08_floor_situational_awareness import WF08_FLOOR_SITUATIONAL_AWARENESS
from .wf09_proactive_service_dispatch import WF09_PROACTIVE_SERVICE_DISPATCH
from .wf10_post_market_surveillance import WF10_POST_MARKET_SURVEILLANCE
from .wf11_account_health_review import WF11_ACCOUNT_HEALTH_REVIEW
from .wf12_patient_admission import WF12_PATIENT_ADMISSION
from .wf13_patient_discharge import WF13_PATIENT_DISCHARGE
from .wf16_recall_impact import WF16_RECALL_IMPACT
from .wf17_renewal_package import WF17_RENEWAL_PACKAGE
from .wf18_competitive_intelligence import WF18_COMPETITIVE_INTELLIGENCE

WORKFLOW_REGISTRY = {
    "fall.detected": WF01_FALL_INVESTIGATION,
    "vital_sign.anomaly": WF02_MEDICATION_CORRELATION,
    "vital_sign.early_warning": WF03_DETERIORATION_CASCADE,
    "device.failure": WF04_DEVICE_FAILURE_IMPACT,
    "patient.discharged": WF05_POST_DISCHARGE_MONITORING,
    "inventory.stockout_risk": WF06_CRITICAL_SHORTAGE_IMPACT,
    "patient.admitted": WF07_ADMISSION_READINESS,
    "floor.briefing": WF08_FLOOR_SITUATIONAL_AWARENESS,
    "field_service.dispatch_needed": WF09_PROACTIVE_SERVICE_DISPATCH,
    "field_service.surveillance": WF10_POST_MARKET_SURVEILLANCE,
    "account.review": WF11_ACCOUNT_HEALTH_REVIEW,
    "patient.admission": WF12_PATIENT_ADMISSION,
    "patient.discharge_memory": WF13_PATIENT_DISCHARGE,
    "device.recall": WF16_RECALL_IMPACT,
    "account.renewal": WF17_RENEWAL_PACKAGE,
    "account.competitive_threat": WF18_COMPETITIVE_INTELLIGENCE,
}

ALL_WORKFLOWS = {
    "WF-01": WF01_FALL_INVESTIGATION,
    "WF-02": WF02_MEDICATION_CORRELATION,
    "WF-03": WF03_DETERIORATION_CASCADE,
    "WF-04": WF04_DEVICE_FAILURE_IMPACT,
    "WF-05": WF05_POST_DISCHARGE_MONITORING,
    "WF-06": WF06_CRITICAL_SHORTAGE_IMPACT,
    "WF-07": WF07_ADMISSION_READINESS,
    "WF-08": WF08_FLOOR_SITUATIONAL_AWARENESS,
    "WF-09": WF09_PROACTIVE_SERVICE_DISPATCH,
    "WF-10": WF10_POST_MARKET_SURVEILLANCE,
    "WF-11": WF11_ACCOUNT_HEALTH_REVIEW,
    "WF-14": WF12_PATIENT_ADMISSION,
    "WF-15": WF13_PATIENT_DISCHARGE,
    "WF-16": WF16_RECALL_IMPACT,
    "WF-17": WF17_RENEWAL_PACKAGE,
    "WF-18": WF18_COMPETITIVE_INTELLIGENCE,
}
