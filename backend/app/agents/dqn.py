"""Small, dependency-light DQN backend for high-dimensional simulation states.

The simulation keeps tabular Q-learning as the deterministic fallback. Set
RL_BACKEND=dqn to enable this neural policy. The network is intentionally
small and CPU-friendly; replay memory is bounded and learning is clipped.
"""
from __future__ import annotations
from collections import deque
from typing import Sequence
import random
import numpy as np
import torch
from torch import nn

class _Net(nn.Module):
    def __init__(self, state_dim: int, action_dim: int):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(state_dim, 64), nn.ReLU(),
            nn.Linear(64, 64), nn.ReLU(),
            nn.Linear(64, action_dim),
        )
    def forward(self, x):
        return self.net(x)

class DQNPolicy:
    def __init__(self, state_dim: int, action_dim: int, gamma=.95, lr=1e-3,
                 epsilon=.20, epsilon_min=.03, epsilon_decay=.999):
        self.state_dim, self.action_dim = state_dim, action_dim
        self.gamma, self.epsilon, self.epsilon_min = gamma, epsilon, epsilon_min
        self.epsilon_decay = epsilon_decay
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.online = _Net(state_dim, action_dim).to(self.device)
        self.target = _Net(state_dim, action_dim).to(self.device)
        self.target.load_state_dict(self.online.state_dict())
        self.optimizer = torch.optim.Adam(self.online.parameters(), lr=lr)
        self.memory = deque(maxlen=5000)
        self.steps = 0

    @staticmethod
    def vectorize(state: dict, keys: Sequence[str]) -> np.ndarray:
        # Normalize all bounded simulation metrics to a stable 0..1 range.
        out=[]
        for k in keys:
            v=float(state.get(k, 0.0) or 0.0)
            if k == "public_sentiment": v=(v+1.0)/2.0
            else: v=v/100.0
            out.append(float(np.clip(v, 0.0, 1.0)))
        return np.asarray(out, dtype=np.float32)

    def select(self, state: dict, keys: Sequence[str]) -> int:
        if random.random() < self.epsilon:
            return random.randrange(self.action_dim)
        x=torch.from_numpy(self.vectorize(state, keys)).unsqueeze(0).to(self.device)
        with torch.no_grad():
            return int(self.online(x).argmax(dim=1).item())

    def learn(self, state, action, reward, next_state, keys, done=False):
        self.memory.append((self.vectorize(state,keys), int(action), float(reward),
                            self.vectorize(next_state,keys), bool(done)))
        self.steps += 1
        if len(self.memory) < 32: return 0.0
        batch=random.sample(self.memory, 32)
        s,a,r,ns,d=zip(*batch)
        s=torch.tensor(np.asarray(s),device=self.device)
        ns=torch.tensor(np.asarray(ns),device=self.device)
        a=torch.tensor(a,dtype=torch.long,device=self.device).unsqueeze(1)
        r=torch.tensor(r,dtype=torch.float32,device=self.device)
        d=torch.tensor(d,dtype=torch.float32,device=self.device)
        q=self.online(s).gather(1,a).squeeze(1)
        with torch.no_grad():
            target=r + (1-d)*self.gamma*self.target(ns).max(1).values
        loss=nn.functional.smooth_l1_loss(q,target)
        self.optimizer.zero_grad(); loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online.parameters(), 1.0)
        self.optimizer.step()
        self.epsilon=max(self.epsilon_min,self.epsilon*self.epsilon_decay)
        if self.steps % 100 == 0:
            self.target.load_state_dict(self.online.state_dict())
        return float(loss.item())
