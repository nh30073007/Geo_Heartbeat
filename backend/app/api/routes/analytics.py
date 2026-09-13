"""
Advanced Analytics Routes with:
- Performance metrics
- Agent analysis
- Equilibrium analysis
- Sentiment analysis
- Report generation
"""
from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json
import logging
import pandas as pd
import io
from pathlib import Path

from ...simulation import SimulationRunner
from ...game_theory import EquilibriumAnalyzer
from ...core.runtime import runtime
from ...analytics.forecast import forecast_metrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Global instances
simulation_runner = runtime.simulation_runner

# Response Models
class AnalyticsResponse(BaseModel):
    """Analytics response"""
    sim_id: str
    metrics: Dict[str, Any]
    timestamp: str

# Routes
@router.get("/forecast/{sim_id}")
async def get_forecast(sim_id: str, horizon: int = Query(8, ge=1, le=30), window: int = Query(30, ge=5, le=200)):
    """
    Short-horizon trend projection for the dashboard's forecast panel.
    Not RL -- see analytics/forecast.py for why a linear-trend model is the
    right tool for this and where to extend it if more accuracy is needed.
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")

        engine = simulation_runner.simulations[sim_id]
        history = engine.get_history(limit=window)
        history_payload = [{'round': s.round, 'state': s.state_snapshot} for s in history]

        result = forecast_metrics(history_payload, horizon=horizon, window=window)

        return {
            'sim_id': sim_id,
            **result,
            'timestamp': datetime.now().isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to compute forecast: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/performance/{sim_id}")
async def get_performance_metrics(sim_id: str):
    """
    Get performance metrics for a simulation
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        engine = simulation_runner.simulations[sim_id]
        metrics = engine.get_performance_metrics()
        
        # Add additional analytics
        history = engine.get_history(limit=100)
        if history:
            # Calculate convergence rate
            stability_values = [s.state_snapshot.get('stability', 0) for s in history]
            if len(stability_values) > 1:
                convergence = (stability_values[-1] - stability_values[0]) / len(stability_values)
                metrics['convergence_rate'] = convergence
            
            # Calculate volatility
            economic_values = [s.state_snapshot.get('economic_stability', 0) for s in history]
            if len(economic_values) > 1:
                metrics['economic_volatility'] = pd.Series(economic_values).std()
        
        return {
            'sim_id': sim_id,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/agents/{sim_id}")
async def get_agent_analysis(sim_id: str):
    """
    Get agent performance analysis
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        engine = simulation_runner.simulations[sim_id]
        
        # Get agent data
        hegemon = engine.hegemon
        sovereign = engine.sovereign
        
        return {
            'sim_id': sim_id,
            'hegemon': {
                'total_utility': hegemon.total_utility,
                'strategy_usage': dict(hegemon.performance['strategy_usage']),
                'success_rate': hegemon.performance['successful_actions'] / max(1, hegemon.performance['total_actions']),
                'avg_response_time': hegemon.performance['avg_response_time'],
                'history': hegemon.get_history(limit=50)
            },
            'sovereign': {
                'total_utility': sovereign.total_utility,
                'strategy_usage': dict(sovereign.performance['strategy_usage']),
                'success_rate': sovereign.performance['successful_actions'] / max(1, sovereign.performance['total_actions']),
                'avg_response_time': sovereign.performance['avg_response_time'],
                'history': sovereign.get_history(limit=50)
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get agent analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/equilibrium/{sim_id}")
async def get_equilibrium_analysis(sim_id: str):
    """
    Get equilibrium analysis
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        engine = simulation_runner.simulations[sim_id]
        state = engine.get_state()
        
        # Get equilibrium analysis
        equilibrium = engine.equilibrium_analyzer.analyze_all(state)
        
        # Format response
        result = {
            'sim_id': sim_id,
            'state': state,
            'equilibria': {}
        }
        
        for eq_type, eq_result in equilibrium.items():
            result['equilibria'][eq_type.value] = {
                'count': len(eq_result.equilibria),
                'stability': eq_result.stability_score,
                'pareto_optimal': eq_result.pareto_optimal,
                'social_welfare': eq_result.social_welfare,
                'fairness': eq_result.fairness_index,
                'equilibria': eq_result.equilibria
            }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get equilibrium analysis: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/sentiment/{sim_id}")
async def get_sentiment_analytics(sim_id: str):
    """
    Get sentiment analytics
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        engine = simulation_runner.simulations[sim_id]
        state = engine.get_state()
        
        # Get sentiment data
        sentiment_state = state.get('public_sentiment', 0)
        history = engine.get_history(limit=100)
        
        # Calculate sentiment trends
        sentiment_history = [s.state_snapshot.get('public_sentiment', 0) for s in history]
        
        return {
            'sim_id': sim_id,
            'current_sentiment': sentiment_state,
            'sentiment_history': sentiment_history,
            'trend': {
                'direction': ('flat' if not sentiment_history or abs(sentiment_history[-1] - sentiment_history[0]) < 1e-6 else ('positive' if sentiment_history[-1] > sentiment_history[0] else 'negative')),
                'change': sentiment_history[-1] - sentiment_history[0] if sentiment_history else 0,
                'volatility': pd.Series(sentiment_history).std() if sentiment_history else 0
            },
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get sentiment analytics: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/report/{sim_id}")
async def generate_report(
    sim_id: str,
    format: str = Query("json", pattern="^(json|pdf|csv)$")
):
    """
    Generate comprehensive analytics report
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        # Gather all data
        performance = await get_performance_metrics(sim_id)
        agents = await get_agent_analysis(sim_id)
        equilibrium = await get_equilibrium_analysis(sim_id)
        sentiment = await get_sentiment_analytics(sim_id)
        
        report = {
            'sim_id': sim_id,
            'generated_at': datetime.now().isoformat(),
            'performance': performance,
            'agents': agents,
            'equilibrium': equilibrium,
            'sentiment': sentiment
        }
        
        if format == "csv":
            # Convert to CSV
            import pandas as pd
            
            # Flatten report for CSV
            flat_data = []
            if 'performance' in report:
                flat_data.append({
                    'metric': 'performance',
                    **report['performance'].get('metrics', {})
                })
            
            df = pd.DataFrame(flat_data)
            output = io.StringIO()
            df.to_csv(output, index=False)
            
            return Response(
                content=output.getvalue(),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=report_{sim_id}.csv"
                }
            )
        
        return report
        
    except Exception as e:
        logger.error(f"Failed to generate report: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/trends/{sim_id}")
async def get_trends(
    sim_id: str,
    metric: str,
    window: int = Query(20, ge=2, le=100)
):
    """
    Get trend analysis for a specific metric
    """
    try:
        if sim_id not in simulation_runner.simulations:
            raise HTTPException(status_code=404, detail="Simulation not found")
        
        engine = simulation_runner.simulations[sim_id]
        history = engine.get_history(limit=window)
        
        values = [s.state_snapshot.get(metric, 0) for s in history]
        
        if not values:
            return {
                'sim_id': sim_id,
                'metric': metric,
                'values': [],
                'trend': 'no_data',
                'timestamp': datetime.now().isoformat()
            }
        
        # Calculate trends
        trend = 'stable'
        if len(values) > 1:
            slope = (values[-1] - values[0]) / len(values)
            if slope > 0.1:
                trend = 'rising'
            elif slope < -0.1:
                trend = 'falling'
        
        return {
            'sim_id': sim_id,
            'metric': metric,
            'values': values,
            'trend': trend,
            'current': values[-1],
            'avg': sum(values) / len(values),
            'min': min(values),
            'max': max(values),
            'volatility': pd.Series(values).std() if len(values) > 1 else 0,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get trends: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/comparison")
async def compare_simulations(
    sim_ids: str,
    metrics: Optional[str] = None
):
    """
    Compare multiple simulations
    """
    try:
        sim_list = sim_ids.split(',')
        compare_metrics = metrics.split(',') if metrics else ['economic_stability', 'public_sentiment']
        
        comparison = {}
        
        for sim_id in sim_list:
            if sim_id not in simulation_runner.simulations:
                continue
            
            engine = simulation_runner.simulations[sim_id]
            state = engine.get_state()
            
            comparison[sim_id] = {
                metric: state.get(metric, 0)
                for metric in compare_metrics
                if metric in state
            }
        
        return {
            'simulations': sim_list,
            'metrics': compare_metrics,
            'comparison': comparison,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to compare simulations: {e}")
        raise HTTPException(status_code=400, detail=str(e))