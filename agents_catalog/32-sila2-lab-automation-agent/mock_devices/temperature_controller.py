import time

class TemperatureController:
    def __init__(self):
        self.current_temp = 25.0
        self.target_temp = None
        self.is_heating = False
        self.heating_status = "idle"  # "idle", "heating", "completed"
        self.start_time = None
        self.scenario_mode = "scenario_2"
        
    def set_scenario_mode(self, mode: str):
        self.scenario_mode = mode
        
    def get_heating_rate(self) -> float:
        return 5.0 if self.scenario_mode == "scenario_1" else 2.0
    
    def set_temperature(self, target: float):
        self.target_temp = target
        self.is_heating = True
        self.heating_status = "heating"
        self.start_time = time.time()
        self.current_temp = 25.0
        
    def get_current_temperature(self) -> float:
        if not self.is_heating or not self.start_time:
            return self.current_temp
            
        elapsed = time.time() - self.start_time
        rate_per_second = self.get_heating_rate() / 60.0
        temp_increase = rate_per_second * elapsed
        self.current_temp = min(25.0 + temp_increase, self.target_temp)
        
        # 目標温度到達チェック
        if self.current_temp >= self.target_temp:
            self.heating_status = "completed"
            self.is_heating = False
        
        return self.current_temp
    
    def check_target_reached(self) -> bool:
        if not self.is_heating:
            return False
        return self.get_current_temperature() >= self.target_temp
    
    def stop_heating(self):
        self.is_heating = False
        if self.heating_status == "heating":
            self.heating_status = "idle"
        
    def toggle_scenario(self):
        if self.scenario_mode == "scenario_1":
            self.scenario_mode = "scenario_2"
        else:
            self.scenario_mode = "scenario_1"
        print(f"Scenario switched to: {self.scenario_mode}")
