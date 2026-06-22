"""
environment.py — Dhaka Residential Demand Response Custom Gym Environment
Uttara University | Department of Electrical and Electronic Engineering
BSc Thesis Project Algorithmic Framework
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
import random

class DhakaDemandResponseEnv(gym.Env):
    """
    A custom energy management environment simulating a middle-income 
    household in Dhaka facing 3-tier ToU pricing and stochastic load shedding.
    """
    metadata = {"render.modes": ["human"]}

    def __init__(self):
        super(DhakaDemandResponseEnv, self).__init__()

        # Action Space: 7 Discrete Composite Actions
        self.action_space = spaces.Discrete(7)

        # Observation Space: 8-Dimensional Continuous Vector (Bounds 0.0 to 1.0)
        self.observation_space = spaces.Box(
            low=0.0, 
            high=1.0, 
            shape=(8,), 
            dtype=np.float32
        )

        # Optimization Reward Coefficients
        self.alpha = 1.0       # Cost coefficient
        self.beta = 0.3        # Peak-to-Average Ratio penalty weight
        self.gamma_c = 0.5     # User comfort violation penalty
        self.delta = 0.4       # Energy arbitrage performance reward

        # Base Technical Specifications of Appliances & Storage
        self.p_washing_machine = 0.80  # Rated Power in kW
        self.p_water_pump = 0.55       # Rated Power in kW
        self.battery_capacity = 5.0    # Total capacity in kWh
        self.max_charge_rate = 1.5     # Max continuous power input in kW
        self.max_discharge_rate = 1.5  # Max continuous power output in kW
        self.battery_efficiency = 0.92 # Round-trip efficiency factor

        # BERC Three-Tier Time-Of-Use Pricing Schedules (BDT per kWh)
        # Off-Peak: 6.5 BDT, Mid-Peak: 10.0 BDT, Peak-Surge: 14.0 BDT
        self.tou_prices = {
            "off_peak": 6.50,
            "mid_peak": 10.00,
            "peak": 14.00
        }

        # Operational State Tracking Variables
        self.current_hour = 0
        self.battery_soc = 0.5
        self.w_pending = 0.80
        self.p_pending = 0.55
        
        # Chronological Load Curves Array Templates for Dhaka Households
        self.base_load_profile = [
            0.4, 0.3, 0.3, 0.3, 0.3, 0.4, 0.5, 0.8, 
            1.2, 1.5, 1.1, 1.0, 0.9, 0.8, 0.9, 1.1, 
            1.4, 2.2, 2.8, 3.1, 2.9, 1.8, 1.1, 0.6
        ]

    def _get_tou_price(self, hour):
        """Helper logic mapping BERC structural tariff tiers based on clock hour"""
        if 23 <= hour or hour < 7:
            return self.tou_prices["off_peak"]
        elif 7 <= hour < 17:
            return self.tou_prices["mid_peak"]
        else:
            return self.tou_prices["peak"]

    def _sample_load_shedding(self, hour):
        """Bernoulli trial modeling empirical outage probabilities of Dhaka grids"""
        if 17 <= hour < 23:
            prob = 0.22  # 22% high failure rate during peak evening surge
        elif 7 <= hour < 17:
            prob = 0.08  # 8% standard operational load shedding risk
        else:
            prob = 0.03  # 3% minimal baseline overnight outage probability
        return 1 if random.random() < prob else 0

    def reset(self, seed=None, options=None):
        """Resets the state vector at the start of each simulated 24-hour episode"""
        super().reset(seed=seed)
        
        self.current_hour = 0
        self.battery_soc = 0.5  # Reset storage system to half capacity
        self.w_pending = 0.80   # Full active task cycle load allocated
        self.p_pending = 0.55   # Full operational pumping target set

        state = self._build_state_vector()
        return state, {}

    def _build_state_vector(self):
        """Assembles and normalizes variables into the 8-dimensional space array"""
        hour_norm = self.current_hour / 23.0
        base_load = self.base_load_profile[self.current_hour]
        price = self._get_tou_price(self.current_hour)
        
        # Max scaling templates for uniform neural network gradient propagation
        base_load_norm = min(base_load / 4.0, 1.0)
        price_norm = price / 14.0
        w_norm = self.w_pending / 0.80
        p_norm = self.p_pending / 0.55
        soc_norm = self.battery_soc
        
        # Mocking synthetic temperature profile cycle
        temp = 28.0 + 6.0 * np.sin(2.0 * np.pi * (self.current_hour - 6) / 24.0)
        temp_norm = (temp - 20.0) / 20.0
        
        shed_active = self._sample_load_shedding(self.current_hour)

        return np.array([
            hour_norm, base_load_norm, price_norm, w_norm, 
            p_norm, soc_norm, temp_norm, float(shed_active)
        ], dtype=np.float32)

    def step(self, action):
        """Executes one step of the scheduling policy inside the environment"""
        state_vars = self._build_state_vector()
        shed_active = state_vars[7] == 1.0
        current_price = self._get_tou_price(self.current_hour)
        base_power = self.base_load_profile[self.current_hour]

        appliance_power = 0.0
        arbitrage_reward = 0.0
        comfort_penalty = 0.0

        # Implement grid override logic during active load shedding events
        if shed_active:
            # Grid failure forces consumption to zero; pending tasks are frozen
            total_load = 0.0
            if action in [1, 2, 3]:
                comfort_penalty += 1.0  # Penalize grid-induced task interruptions
        else:
            # Standard connection logic: parse structural action configurations
            if action == 0:
                pass  # All flexible loads deferred
            elif action == 1:
                if self.w_pending > 0:
                    appliance_power += self.p_washing_machine
                    self.w_pending = max(0.0, self.w_pending - self.p_washing_machine)
            elif action == 2:
                if self.p_pending > 0:
                    appliance_power += self.p_water_pump
                    self.p_pending = max(0.0, self.p_pending - self.p_water_pump)
            elif action == 3:
                if self.w_pending > 0:
                    appliance_power += self.p_washing_machine
                    self.w_pending = max(0.0, self.w_pending - self.p_washing_machine)
                if self.p_pending > 0:
                    appliance_power += self.p_water_pump
                    self.p_pending = max(0.0, self.p_pending - self.p_water_pump)
            elif action == 4:
                # Charge battery from grid lines up to max capacity bounds
                charge_space = (1.0 - self.battery_soc) * self.battery_capacity
                actual_charge = min(self.max_charge_rate, charge_space)
                self.battery_soc += (actual_charge * self.battery_efficiency) / self.battery_capacity
                appliance_power += actual_charge
            elif action == 5:
                # Discharge battery to offset household demand
                available_energy = self.battery_soc * self.battery_capacity
                actual_discharge = min(self.max_discharge_rate, available_energy)
                self.battery_soc -= actual_discharge / self.battery_capacity
                appliance_power -= actual_discharge
                arbitrage_reward += actual_discharge * current_price
            elif action == 6:
                # Voluntary 50% partial load shaving
                if self.w_pending > 0:
                    appliance_power += (self.p_washing_machine * 0.5)
                    self.w_pending = max(0.0, self.w_pending - (self.p_washing_machine * 0.5))

            total_load = max(0.0, base_power + appliance_power)

        # Mathematical formulation of the multi-objective reward signal
        cost = total_load * current_price
        
        # Compute Peak-to-Average Ratio rolling target baseline variations
        avg_target_load = 1.2
        par_penalty = max(0.0, total_load - avg_target_load) / avg_target_load

        # Check for missed deadlines at the end of critical operational windows
        if self.current_hour == 9 and self.p_pending > 0:
            comfort_penalty += 2.0  # Missed water pump deadline
        if self.current_hour == 22 and self.w_pending > 0:
            comfort_penalty += 2.0  # Missed washing machine deadline

        # Composite Reward Equation Formulation
        reward = -(self.alpha * cost) - (self.beta * par_penalty) - (self.gamma_c * comfort_penalty) + (self.delta * arbitrage_reward)

        # Advance timeline mechanics
        self.current_hour += 1
        done = True if self.current_hour >= 24 else False
        
        next_state = self._build_state_vector()
        truncated = False

        return next_state, reward, done, truncated, {}