from __future__ import annotations

import asyncio
import sys
import os
import time
from datetime import timedelta
from typing import TYPE_CHECKING
from queue import Queue

from sila2.server import MetadataDict, ObservableCommandInstanceWithIntermediateResponses

from ..generated.temperaturecontroller import (
    AbortExperiment_Responses,
    SetTemperature_IntermediateResponses,
    SetTemperature_Responses,
    TemperatureControllerBase,
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
from temperature_controller import TemperatureController

if TYPE_CHECKING:
    from ..server import Server


class TemperatureControllerImpl(TemperatureControllerBase):
    def __init__(self, parent_server: Server) -> None:
        super().__init__(parent_server=parent_server)
        self.controller = TemperatureController()
        self.SetTemperature_default_lifetime_of_execution = timedelta(minutes=30)
        
        # Observable property queues
        self._CurrentTemperature_producer_queue: Queue[float] = Queue()
        self._TargetTemperature_producer_queue: Queue[float] = Queue()
        self._HeatingStatus_producer_queue: Queue[dict] = Queue()
        
        # Start periodic updates
        self.run_periodically(
            lambda: self._CurrentTemperature_producer_queue.put(self.controller.get_current_temperature()),
            delay_seconds=0.5
        )
        self.run_periodically(
            lambda: self._TargetTemperature_producer_queue.put(self.controller.target_temp or 0.0),
            delay_seconds=1.0
        )
        self.run_periodically(
            lambda: self._HeatingStatus_producer_queue.put(self._get_heating_status_dict()),
            delay_seconds=0.5
        )
    
    def _get_heating_status_dict(self) -> dict:
        elapsed = int(time.time() - self.controller.start_time) if self.controller.start_time else 0
        return {
            'IsHeating': self.controller.is_heating,
            'ElapsedSeconds': elapsed,
            'ScenarioMode': self.controller.scenario_mode
        }

    def AbortExperiment(self, *, metadata: MetadataDict) -> AbortExperiment_Responses:
        self.controller.stop_heating()
        self.controller.target_temp = None
        return AbortExperiment_Responses()

    def SetTemperature(
        self,
        TargetTemperature: float,
        *,
        metadata: MetadataDict,
        instance: ObservableCommandInstanceWithIntermediateResponses[SetTemperature_IntermediateResponses],
    ) -> SetTemperature_Responses:
        instance.begin_execution()
        self.controller.set_temperature(TargetTemperature)
        
        while self.controller.is_heating:
            current = self.controller.get_current_temperature()
            elapsed = int(time.time() - self.controller.start_time) if self.controller.start_time else 0
            percent = int((current - 25.0) / (TargetTemperature - 25.0) * 100) if TargetTemperature > 25.0 else 100
            
            instance.send_intermediate_response(
                SetTemperature_IntermediateResponses(
                    Progress={
                        'CurrentTemperature': current,
                        'PercentComplete': min(percent, 100),
                        'ElapsedSeconds': elapsed
                    }
                )
            )
            time.sleep(0.5)
        
        return SetTemperature_Responses()
    
    def get_CurrentTemperature(self, *, metadata: MetadataDict) -> float:
        return self.controller.get_current_temperature()
    
    def get_TargetTemperature(self, *, metadata: MetadataDict) -> float:
        return self.controller.target_temp or 0.0
    
    def get_HeatingStatus(self, *, metadata: MetadataDict) -> dict:
        elapsed = int(time.time() - self.controller.start_time) if self.controller.start_time else 0
        return {
            'IsHeating': self.controller.is_heating,
            'ElapsedSeconds': elapsed,
            'ScenarioMode': self.controller.scenario_mode
        }
