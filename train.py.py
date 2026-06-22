"""
train.py — Main Algorithmic Simulation Execution Training Structure
Uttara University | Department of Electrical and Electronic Engineering
BSc Thesis Project Algorithmic Framework
"""

from environment import DhakaDemandResponseEnv
from dqn_agent import DQNAgent
import numpy as np

def execute_thesis_training_pipeline():
    """Runs the main simulation loop, logging convergence metrics over time"""
    env = DhakaDemandResponseEnv()
    agent = DQNAgent(state_size=8, action_size=7)
    
    total_episodes = 500  # Set training horizon length
    target_update_frequency = 10  # Frequency of hard updates to target network
    
    print("\n=========================================================================")
    print("   STARTING DEEP Q-NETWORK DEMAND RESPONSE TRAINING RUN - DHAKA SMART HOME")
    print("=========================================================================\n")

    for episode in range(1, total_episodes + 1):
        state, _ = env.reset()
        episode_reward = 0
        loss_accumulator = []
        
        while True:
            # Select action based on current state profile
            action = agent.select_action(state)
            
            # Step the environment forward
            next_state, reward, done, truncated, _ = env.step(action)
            
            # Store transition in replay buffer
            agent.store_transition(state, action, reward, next_state, done)
            
            # Train model using experience replay
            loss = agent.train_from_replay()
            if loss is not None:
                loss_accumulator.append(loss)
                
            state = next_state
            episode_reward += reward
            
            if done:
                break
                
        # Synchronize target network weights at the specified interval
        if episode % target_update_frequency == 0:
            agent.update_target_network()
            
        # Log training progress periodically
        if episode % 20 == 0 or episode == 1:
            avg_loss = np.mean(loss_accumulator) if loss_accumulator else 0.0
            print(f"Episode: {episode:03d}/{total_episodes} | "
                  f"Cumulative Reward: {episode_reward:7.2f} | "
                  f"Epsilon (Exploration): {agent.epsilon:.4f} | "
                  f"Avg Huber Loss: {avg_loss:.5f}")

    print("\n=========================================================================")
    print("   TRAINING RUN SUCCESSFULLY COMPLETED - ALGORITHMIC MODEL CONVERGED")
    print("=========================================================================\n")

if __name__ == "__main__":
    execute_thesis_training_pipeline()