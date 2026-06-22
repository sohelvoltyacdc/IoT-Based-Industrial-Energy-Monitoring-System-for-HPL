"""
dqn_agent.py — Deep Q-Network Core Intelligent Controller
Uttara University | Department of Electrical and Electronic Engineering
BSc Thesis Project Algorithmic Framework
"""

import numpy as np
import tensorflow as tf
from collections import deque
import random

class DQNAgent:
    """
    DQN Agent utilizing Experience Replay, Target Networks,
    and Huber Loss minimization for stable load scheduling policies.
    """
    def __init__(self, state_size=8, action_size=7):
        self.state_size = state_size
        self.action_size = action_size
        
        # Experience Replay Deque Buffer Allocation
        self.memory = deque(maxlen=10000)
        
        # Algorithmic Hyperparameters
        self.gamma = 0.95        # Discount Factor for future rewards
        self.epsilon = 1.00      # Exploration schedule start value
        self.eps_min = 0.01      # Minimum floor boundary for exploration
        self.eps_decay = 0.995   # Geometric decay rate per episode
        self.learning_rate = 0.001
        self.batch_size = 32     # Minibatch extraction size from replay buffer
        
        # Instantiate Online and Target Evaluation Networks
        self.model = self._build_neural_architecture()
        self.target_model = self._build_neural_architecture()
        self.update_target_network()

    def _build_neural_architecture(self):
        """Constructs the feedforward fully-connected deep neural mapping layers"""
        model = tf.keras.Sequential([
            tf.keras.layers.Dense(64, activation='relu', input_shape=(self.state_size,), name='Input_FC64'),
            tf.keras.layers.Dense(128, activation='relu', name='Hidden_FC128'),
            tf.keras.layers.Dense(64, activation='relu', name='Hidden_FC64'),
            tf.keras.layers.Dense(self.action_size, activation='linear', name='Output_Values7')
        ])
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=self.learning_rate),
            loss=tf.keras.losses.Huber()  # Huber loss provides robust clipping against gradient anomalies
        )
        return model

    def update_target_network(self):
        """Hard update rule: overwrites target network weights with online network parameters"""
        self.target_model.set_weights(self.model.get_weights())

    def store_transition(self, state, action, reward, next_state, done):
        """Appends an experience transition tuple to the circular memory buffer"""
        self.memory.append((state, action, reward, next_state, done))

    def select_action(self, state):
        """Selects actions using an epsilon-greedy exploration vs exploitation scheme"""
        if np.random.rand() < self.epsilon:
            return random.randrange(self.action_size)  # Explore random action paths
        
        # Exploit: feed forward the state through the network to evaluate optimal actions
        q_values = self.model.predict(state.reshape(1, -1), verbose=0)
        return int(np.argmax(q_values[0]))

    def train_from_replay(self):
        """Samples experiences, computes Temporal Difference targets, and updates weights"""
        if len(self.memory) < self.batch_size:
            return None  # Ensure memory has sufficient samples before starting optimization

        # Sample a random, uncorrelated batch of experiences
        minibatch = random.sample(self.memory, self.batch_size)
        
        states = np.array([transition[0] for transition in minibatch])
        actions = np.array([transition[1] for transition in minibatch])
        rewards = np.array([transition[2] for transition in minibatch])
        next_states = np.array([transition[3] for transition in minibatch])
        dones = np.array([transition[4] for transition in minibatch])

        # Generate current Q-value predictions using the online network
        q_current = self.model.predict(states, verbose=0)
        
        # Generate future target Q-values using the frozen target network
        q_target_next = self.target_model.predict(next_states, verbose=0)

        for idx in range(self.batch_size):
            if dones[idx]:
                q_current[idx][actions[idx]] = rewards[idx]
            else:
                # Bellman Optimality Equation formulation integration
                q_current[idx][actions[idx]] = rewards[idx] + self.gamma * np.max(q_target_next[idx])

        # Execute gradient descent step on the online network
        history = self.model.fit(states, q_current, epochs=1, verbose=0)
        loss_val = history.history['loss'][0]

        # Decay exploration probability over time
        if self.epsilon > self.eps_min:
            self.epsilon *= self.eps_decay

        return loss_val