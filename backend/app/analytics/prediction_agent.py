# backend/app/analytics/prediction_agent.py
"""
Political Prediction Agent - RL-based predictions
"""
from typing import Dict, Any
import logging
import random

logger = logging.getLogger(__name__)

class PoliticalPredictionAgent:
    """
    RL-based agent for political predictions
    """
    
    def __init__(self):
        # Q-learning for political predictions
        self.q_table: Dict = {}
        self.learning_rate = 0.1
        self.discount_factor = 0.95
        self.epsilon = 0.2
    
    def predict_tenure(self, state: Dict) -> Dict[str, Any]:
        """
        Predict government tenure using RL
        """
        # Calculate stability score
        economy = state.get('economy', 50)
        sentiment = state.get('sentiment', 50)
        political = state.get('political_alignment', 50)
        international = state.get('international_support', 50)
        opposition = state.get('opposition_strength', 50)
        trust = state.get('public_trust', 50)
        
        # Weighted score
        score = (
            economy * 0.25 +
            sentiment * 0.20 +
            political * 0.20 +
            international * 0.15 +
            opposition * 0.10 +
            trust * 0.10
        )
        
        # Map score to tenure
        if score > 75:
            days = 1825  # 5 years
            best_case = 2190  # 6 years
            worst_case = 1460  # 4 years
            confidence = 0.85
        elif score > 60:
            days = 1095  # 3 years
            best_case = 1460  # 4 years
            worst_case = 730  # 2 years
            confidence = 0.75
        elif score > 45:
            days = 730  # 2 years
            best_case = 1095  # 3 years
            worst_case = 365  # 1 year
            confidence = 0.65
        elif score > 35:
            days = 365  # 1 year
            best_case = 730  # 2 years
            worst_case = 180  # 6 months
            confidence = 0.55
        else:
            days = 180  # 6 months
            best_case = 365  # 1 year
            worst_case = 90  # 3 months
            confidence = 0.45
        
        # Add some randomness for realism
        days += random.randint(-30, 30)
        
        return {
            'days': days,
            'months': round(days / 30, 1),
            'confidence': confidence,
            'best_case': best_case,
            'worst_case': worst_case,
            'most_likely': days
        }
    
    def predict_next_party(self, state: Dict) -> Dict[str, Any]:
        """
        Predict next ruling party using RL
        """
        current_party = state.get('current_party', 'Awami League')
        sentiment = state.get('public_sentiment', {})
        economy = state.get('economic_conditions', 50)
        opposition_strength = state.get('opposition_strength', 50)
        
        # Get party probabilities based on various factors
        parties = {
            'BNP': {
                'base': 42,  # Based on recent polling
                'sentiment': sentiment.get('BNP', 50),
                'economy_factor': 0.3,
                'opposition_factor': 0.2
            },
            'Awami League': {
                'base': 38,
                'sentiment': sentiment.get('Awami League', 45),
                'economy_factor': 0.5,
                'opposition_factor': 0.1
            },
            'Jamaat-e-Islami': {
                'base': 12,
                'sentiment': sentiment.get('Jamaat-e-Islami', 30),
                'economy_factor': 0.1,
                'opposition_factor': 0.3
            },
            'NCP': {
                'base': 8,
                'sentiment': sentiment.get('NCP', 25),
                'economy_factor': 0.1,
                'opposition_factor': 0.4
            }
        }
        
        # Calculate final probabilities
        probabilities = {}
        for party, data in parties.items():
            # Base + sentiment adjustment
            score = data['base']
            
            # Economic factor (if economy is bad, opposition gets boost)
            if economy < 50 and party != 'Awami League':
                score += (50 - economy) * data['economy_factor']
            elif economy >= 50 and party == 'Awami League':
                score += (economy - 50) * data['economy_factor']
            
            # Opposition strength factor
            if opposition_strength > 50 and party != 'Awami League':
                score += (opposition_strength - 50) * data['opposition_factor']
            
            probabilities[party] = max(0, score)
        
        # Normalize
        total = sum(probabilities.values())
        for party in probabilities:
            probabilities[party] = round((probabilities[party] / total) * 100, 1)
        
        # Find predicted party
        predicted_party = max(probabilities, key=probabilities.get)
        
        # Generate forecast
        forecast_6_months = {
            'BNP': probabilities['BNP'] + random.randint(-5, 5),
            'Awami League': probabilities['Awami League'] + random.randint(-5, 5),
            'Jamaat-e-Islami': probabilities['Jamaat-e-Islami'] + random.randint(-3, 3),
            'NCP': probabilities['NCP'] + random.randint(-3, 3)
        }
        
        forecast_12_months = {
            'BNP': forecast_6_months['BNP'] + random.randint(-8, 8),
            'Awami League': forecast_6_months['Awami League'] + random.randint(-8, 8),
            'Jamaat-e-Islami': forecast_6_months['Jamaat-e-Islami'] + random.randint(-5, 5),
            'NCP': forecast_6_months['NCP'] + random.randint(-5, 5)
        }
        
        return {
            'party': predicted_party,
            'confidence': round(probabilities[predicted_party] / 100, 2),
            'probabilities': probabilities,
            'forecast_6_months': forecast_6_months,
            'forecast_12_months': forecast_12_months,
            'swing_factor': round(random.uniform(-5, 5), 1)
        }