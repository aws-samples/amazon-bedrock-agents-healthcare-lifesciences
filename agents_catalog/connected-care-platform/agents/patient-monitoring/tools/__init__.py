"""Patient Monitoring Agent Tools"""

from .get_patient_vitals import get_patient_vitals
from .get_vital_sign_history import get_vital_sign_history
from .list_patients import list_patients
from .get_patient_profile import get_patient_profile
from .analyze_vital_trends import analyze_vital_trends
from .get_alert_thresholds import get_alert_thresholds
from .update_alert_threshold import update_alert_threshold
from .publish_clinical_event import publish_clinical_event
from .evaluate_alert_significance import evaluate_alert_significance
from .get_suppressed_alerts import get_suppressed_alerts
from .initialize_patient_memory import initialize_patient_memory
from .record_clinical_observation import record_clinical_observation
from .get_patient_timeline import get_patient_timeline
from .assess_discharge_readiness import assess_discharge_readiness
from .clear_patient_memory import clear_patient_memory
from .recall_patient_memory import recall_patient_memory

ALL_TOOLS = [
    get_patient_vitals,
    get_vital_sign_history,
    list_patients,
    get_patient_profile,
    analyze_vital_trends,
    get_alert_thresholds,
    update_alert_threshold,
    publish_clinical_event,
    evaluate_alert_significance,
    get_suppressed_alerts,
    initialize_patient_memory,
    record_clinical_observation,
    get_patient_timeline,
    assess_discharge_readiness,
    clear_patient_memory,
    recall_patient_memory,
]
