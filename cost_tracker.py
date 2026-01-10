#!/usr/bin/env python3
"""
Advanced Cost Tracking & Analysis System
Filosofia: Se você não mede, você não otimiza. Se você não otimiza, você queima cash.

Features:
- Granular cost tracking (GPU, CPU, storage, network)
- Cost-efficiency analysis (accuracy per dollar)
- Resource utilization patterns
- Optimization recommendations
- Budget forecasting
"""

import mlflow
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class CostConfig:
    """Cost configuration - ajusta conforme teu provider"""
    # Compute costs (USD per hour)
    gpu_a100_cost: float = 0.90      # Oracle Cloud A100
    gpu_v100_cost: float = 0.50      # AWS p3
    gpu_t4_cost: float = 0.35        # GCP T4
    cpu_cost: float = 0.048          # Per vCPU hour
    
    # Storage costs (USD per GB-month)
    ssd_cost: float = 0.10
    hdd_cost: float = 0.02
    s3_standard: float = 0.023
    s3_ia: float = 0.0125            # Infrequent access
    
    # Network costs (USD per GB)
    network_egress: float = 0.09
    network_inter_region: float = 0.02
    
    # MLflow overhead
    mlflow_tracking_overhead: float = 0.01  # Per run
    
    @classmethod
    def from_provider(cls, provider: str) -> 'CostConfig':
        """Load provider-specific pricing"""
        configs = {
            "oracle": cls(
                gpu_a100_cost=0.90,
                cpu_cost=0.048,
                ssd_cost=0.085,
            ),
            "aws": cls(
                gpu_v100_cost=3.06,  # p3.2xlarge on-demand
                cpu_cost=0.096,
                ssd_cost=0.10,
            ),
            "gcp": cls(
                gpu_t4_cost=0.35,
                cpu_cost=0.04,
                ssd_cost=0.17,
            ),
            "lambda": cls(
                gpu_a100_cost=1.10,  # Lambda Labs
                cpu_cost=0.05,
                ssd_cost=0.20,
            ),
        }
        return configs.get(provider.lower(), cls())


class CostTracker:
    """Advanced cost tracking and analysis"""
    
    def __init__(
        self, 
        mlflow_uri: str = "http://localhost:5000",
        cost_config: Optional[CostConfig] = None
    ):
        self.mlflow_uri = mlflow_uri
        self.cost_config = cost_config or CostConfig()
        mlflow.set_tracking_uri(mlflow_uri)
    
    def analyze_experiment(self, experiment_name: str) -> Dict:
        """
        Comprehensive cost analysis de um experiment
        
        Returns metrics tipo:
        - Total cost breakdown
        - Cost per accuracy point
        - Resource utilization
        - Optimization opportunities
        """
        experiment = mlflow.get_experiment_by_name(experiment_name)
        if not experiment:
            raise ValueError(f"Experiment {experiment_name} not found")
        
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        
        if runs.empty:
            return {"error": "No runs found"}
        
        # Calculate costs
        costs = self._calculate_costs(runs)
        
        # Performance metrics
        performance = self._analyze_performance(runs)
        
        # Resource utilization
        utilization = self._analyze_utilization(runs)
        
        # Optimization recommendations
        recommendations = self._generate_recommendations(runs, costs, utilization)
        
        return {
            "experiment": experiment_name,
            "summary": {
                "total_runs": len(runs),
                "successful_runs": len(runs[runs["status"] == "FINISHED"]),
                "total_cost": costs["total"],
                "average_cost_per_run": costs["total"] / len(runs),
                "best_accuracy": performance["best_accuracy"],
                "cost_per_accuracy_point": costs["total"] / (performance["best_accuracy"] * 100),
            },
            "cost_breakdown": costs,
            "performance": performance,
            "utilization": utilization,
            "recommendations": recommendations,
            "timestamp": datetime.now().isoformat(),
        }
    
    def _calculate_costs(self, runs: pd.DataFrame) -> Dict:
        """Calculate detailed cost breakdown"""
        
        # GPU costs
        gpu_hours = runs.get("metrics.training_time", pd.Series([0])).sum() / 3600
        gpu_cost = gpu_hours * self.cost_config.gpu_a100_cost
        
        # CPU costs (assume 8 vCPUs per run em média)
        cpu_hours = runs.get("metrics.training_time", pd.Series([0])).sum() / 3600
        cpu_cost = cpu_hours * 8 * self.cost_config.cpu_cost
        
        # Storage costs (MLflow artifacts)
        # Approximate: cada run gera ~500MB de artifacts
        storage_gb_month = (len(runs) * 0.5)  # GB
        storage_cost = storage_gb_month * self.cost_config.ssd_cost
        
        # MLflow tracking overhead
        tracking_cost = len(runs) * self.cost_config.mlflow_tracking_overhead
        
        total_cost = gpu_cost + cpu_cost + storage_cost + tracking_cost
        
        return {
            "total": total_cost,
            "gpu": gpu_cost,
            "cpu": cpu_cost,
            "storage": storage_cost,
            "tracking": tracking_cost,
            "breakdown": {
                "gpu_hours": gpu_hours,
                "cpu_hours": cpu_hours * 8,  # Total vCPU hours
                "storage_gb": storage_gb_month,
            }
        }
    
    def _analyze_performance(self, runs: pd.DataFrame) -> Dict:
        """Analyze performance metrics"""
        
        successful = runs[runs["status"] == "FINISHED"]
        
        if successful.empty:
            return {"error": "No successful runs"}
        
        accuracies = successful.get("metrics.final_accuracy", pd.Series([0]))
        losses = successful.get("metrics.final_loss", pd.Series([float('inf')]))
        times = successful.get("metrics.training_time", pd.Series([0]))
        
        return {
            "best_accuracy": accuracies.max() if not accuracies.empty else 0,
            "mean_accuracy": accuracies.mean() if not accuracies.empty else 0,
            "std_accuracy": accuracies.std() if not accuracies.empty else 0,
            "best_loss": losses.min() if not losses.empty else float('inf'),
            "mean_training_time": times.mean() if not times.empty else 0,
            "fastest_run": times.min() if not times.empty else 0,
            "slowest_run": times.max() if not times.empty else 0,
        }
    
    def _analyze_utilization(self, runs: pd.DataFrame) -> Dict:
        """Analyze resource utilization patterns"""
        
        successful = runs[runs["status"] == "FINISHED"]
        failed = runs[runs["status"] != "FINISHED"]
        
        # Success rate
        success_rate = len(successful) / len(runs) if len(runs) > 0 else 0
        
        # Time distribution
        times = successful.get("metrics.training_time", pd.Series([0]))
        
        # Hyperparameter efficiency
        if "params.batch_size" in runs.columns:
            batch_sizes = runs["params.batch_size"].value_counts()
            best_batch = batch_sizes.idxmax() if not batch_sizes.empty else None
        else:
            best_batch = None
        
        return {
            "success_rate": success_rate,
            "failed_runs": len(failed),
            "wasted_cost_on_failures": len(failed) * 0.1,  # Approximate
            "time_distribution": {
                "min": times.min() if not times.empty else 0,
                "p25": times.quantile(0.25) if not times.empty else 0,
                "median": times.median() if not times.empty else 0,
                "p75": times.quantile(0.75) if not times.empty else 0,
                "max": times.max() if not times.empty else 0,
            },
            "most_efficient_batch_size": best_batch,
        }
    
    def _generate_recommendations(
        self, 
        runs: pd.DataFrame, 
        costs: Dict, 
        utilization: Dict
    ) -> List[str]:
        """Generate optimization recommendations"""
        
        recommendations = []
        
        # Success rate optimization
        if utilization["success_rate"] < 0.8:
            recommendations.append(
                f"⚠️  Low success rate ({utilization['success_rate']:.1%}). "
                f"Consider tighter hyperparameter bounds or early stopping. "
                f"Potential savings: ${utilization['wasted_cost_on_failures']:.2f}"
            )
        
        # GPU utilization
        gpu_hours = costs["breakdown"]["gpu_hours"]
        if gpu_hours > 100:
            recommendations.append(
                f"💡 High GPU usage ({gpu_hours:.1f}h). "
                f"Consider spot instances for ~70% cost reduction. "
                f"Potential savings: ${costs['gpu'] * 0.7:.2f}"
            )
        
        # Batch size optimization
        if utilization.get("most_efficient_batch_size"):
            recommendations.append(
                f"📊 Most efficient batch size: {utilization['most_efficient_batch_size']}. "
                f"Standardize on this for future runs."
            )
        
        # Storage optimization
        storage_gb = costs["breakdown"]["storage_gb"]
        if storage_gb > 50:
            recommendations.append(
                f"💾 High storage usage ({storage_gb:.1f}GB). "
                f"Archive old runs to S3 Infrequent Access. "
                f"Potential savings: ${storage_gb * (self.cost_config.ssd_cost - self.cost_config.s3_ia):.2f}/month"
            )
        
        # Parallelization opportunity
        successful = runs[runs["status"] == "FINISHED"]
        if not successful.empty:
            avg_time = successful["metrics.training_time"].mean()
            if avg_time > 3600:  # > 1 hour
                recommendations.append(
                    f"⚡ Long average training time ({avg_time/3600:.1f}h). "
                    f"Consider distributed training or model parallelism."
                )
        
        return recommendations
    
    def compare_experiments(self, experiment_names: List[str]) -> pd.DataFrame:
        """Compare multiple experiments side-by-side"""
        
        comparisons = []
        
        for name in experiment_names:
            try:
                analysis = self.analyze_experiment(name)
                comparisons.append({
                    "Experiment": name,
                    "Total Cost": f"${analysis['summary']['total_cost']:.2f}",
                    "Runs": analysis['summary']['total_runs'],
                    "Success Rate": f"{analysis['utilization']['success_rate']:.1%}",
                    "Best Accuracy": f"{analysis['summary']['best_accuracy']:.4f}",
                    "Cost/Acc Point": f"${analysis['summary']['cost_per_accuracy_point']:.3f}",
                    "GPU Hours": f"{analysis['cost_breakdown']['breakdown']['gpu_hours']:.1f}h",
                })
            except Exception as e:
                comparisons.append({
                    "Experiment": name,
                    "Error": str(e)
                })
        
        return pd.DataFrame(comparisons)
    
    def forecast_budget(
        self, 
        experiment_name: str, 
        target_runs: int,
        confidence_level: float = 0.95
    ) -> Dict:
        """Forecast budget for additional runs"""
        
        analysis = self.analyze_experiment(experiment_name)
        
        if "error" in analysis:
            return analysis
        
        avg_cost = analysis["summary"]["average_cost_per_run"]
        
        # Historical variance
        experiment = mlflow.get_experiment_by_name(experiment_name)
        runs = mlflow.search_runs(experiment_ids=[experiment.experiment_id])
        
        times = runs.get("metrics.training_time", pd.Series([0]))
        time_std = times.std() if not times.empty else 0
        
        # Monte Carlo simulation
        np.random.seed(42)
        simulated_costs = np.random.normal(
            avg_cost, 
            avg_cost * 0.2,  # 20% variance
            size=target_runs
        )
        
        # Confidence interval
        lower_bound = np.percentile(simulated_costs.cumsum(), (1 - confidence_level) * 100 / 2)
        upper_bound = np.percentile(simulated_costs.cumsum(), (1 + confidence_level) * 100 / 2)
        expected = simulated_costs.sum()
        
        return {
            "target_runs": target_runs,
            "expected_cost": expected,
            "confidence_interval": {
                "level": confidence_level,
                "lower": lower_bound,
                "upper": upper_bound,
            },
            "per_run_estimate": avg_cost,
            "total_budget_recommendation": upper_bound * 1.1,  # 10% buffer
        }
    
    def export_report(
        self, 
        experiment_name: str, 
        output_file: str = "cost_report.json"
    ):
        """Export detailed cost report"""
        
        analysis = self.analyze_experiment(experiment_name)
        
        # Add metadata
        analysis["report_metadata"] = {
            "generated_at": datetime.now().isoformat(),
            "mlflow_uri": self.mlflow_uri,
            "cost_config": {
                "gpu_cost_per_hour": self.cost_config.gpu_a100_cost,
                "cpu_cost_per_hour": self.cost_config.cpu_cost,
            }
        }
        
        Path(output_file).write_text(json.dumps(analysis, indent=2))
        print(f"Report exported to {output_file}")
        
        return analysis


def main():
    """CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Advanced ML Pipeline Cost Tracking")
    parser.add_argument("command", choices=[
        "analyze", "compare", "forecast", "report"
    ])
    parser.add_argument("--experiment", "-e", help="Experiment name")
    parser.add_argument("--experiments", "-E", nargs="+", help="Multiple experiments")
    parser.add_argument("--target-runs", "-t", type=int, help="Target runs for forecast")
    parser.add_argument("--output", "-o", default="cost_report.json", help="Output file")
    parser.add_argument("--provider", "-p", default="oracle", help="Cloud provider")
    
    args = parser.parse_args()
    
    # Initialize tracker
    config = CostConfig.from_provider(args.provider)
    tracker = CostTracker(cost_config=config)
    
    if args.command == "analyze":
        if not args.experiment:
            print("Error: --experiment required")
            return
        
        analysis = tracker.analyze_experiment(args.experiment)
        
        print("\n" + "="*80)
        print(f"Cost Analysis: {args.experiment}")
        print("="*80)
        print(f"\n📊 Summary:")
        for key, value in analysis["summary"].items():
            print(f"  {key}: {value}")
        
        print(f"\n💰 Cost Breakdown:")
        for key, value in analysis["cost_breakdown"].items():
            if key != "breakdown":
                print(f"  {key}: ${value:.2f}")
        
        print(f"\n⚡ Performance:")
        for key, value in analysis["performance"].items():
            print(f"  {key}: {value}")
        
        print(f"\n💡 Recommendations:")
        for rec in analysis["recommendations"]:
            print(f"  • {rec}")
    
    elif args.command == "compare":
        if not args.experiments:
            print("Error: --experiments required")
            return
        
        df = tracker.compare_experiments(args.experiments)
        print("\n" + df.to_string(index=False))
    
    elif args.command == "forecast":
        if not args.experiment or not args.target_runs:
            print("Error: --experiment and --target-runs required")
            return
        
        forecast = tracker.forecast_budget(args.experiment, args.target_runs)
        
        print(f"\n📈 Budget Forecast: {args.experiment}")
        print(f"Target Runs: {forecast['target_runs']}")
        print(f"Expected Cost: ${forecast['expected_cost']:.2f}")
        print(f"95% CI: ${forecast['confidence_interval']['lower']:.2f} - ${forecast['confidence_interval']['upper']:.2f}")
        print(f"Recommended Budget: ${forecast['total_budget_recommendation']:.2f}")
    
    elif args.command == "report":
        if not args.experiment:
            print("Error: --experiment required")
            return
        
        tracker.export_report(args.experiment, args.output)


# ============================================================================
# CEREBRO Integration - GCP Credit Validation
# ============================================================================

class CerebroCreditValidator:
    """
    Integrates CEREBRO's BillingAuditor for real-time GCP credit validation

    Features:
    - Real-time credit balance check (no 24-48h billing panel latency)
    - Pre-flight validation before expensive runs
    - Credit consumption forecasting
    - Auto-recommendation when credits low

    GCP Project: gen-lang-client-0530325234
    """

    def __init__(
        self,
        project_id: str = "gen-lang-client-0530325234",
        billing_dataset: str = "billing_export"
    ):
        self.project_id = project_id
        self.billing_dataset = billing_dataset
        self.auditor = None

        try:
            # Import CEREBRO's BillingAuditor
            import sys
            cerebro_path = Path("/home/kernelcore/dev/low-level/cerebro")
            if cerebro_path.exists():
                sys.path.insert(0, str(cerebro_path))

            from src.phantom.core.gcp.billing import BillingAuditor

            self.auditor = BillingAuditor(
                project_id=project_id,
                billing_dataset=billing_dataset
            )
            print(f"✅ CEREBRO BillingAuditor initialized")
            print(f"   GCP Project: {project_id}")
            print(f"   Billing Dataset: {billing_dataset}")

        except ImportError as e:
            print(f"⚠️  CEREBRO not available: {e}")
            print(f"   Credit validation will be disabled")
            self.auditor = None

    def validate_credits_before_run(
        self,
        estimated_cost: float,
        days_back: int = 1
    ) -> Dict:
        """
        Pre-flight credit validation

        Args:
            estimated_cost: Estimated cost of upcoming run (USD)
            days_back: Days to look back for credit consumption

        Returns:
            Dict with:
            - approved: bool
            - reason: str (if not approved)
            - recommendation: str
            - credits_remaining: float
            - burn_rate_per_day: float
        """

        if not self.auditor:
            # No auditor = no validation (fail open)
            return {
                "approved": True,
                "reason": "CEREBRO auditor not available",
                "credits_remaining": float('inf'),
                "burn_rate_per_day": 0
            }

        try:
            # Get credit consumption status
            status = self.auditor.audit_credit_consumption(days_back=days_back)

            # Extract metrics
            total_net_cost = status.get('total_net_cost', 0)

            # If net cost is negative, we're using credits (good!)
            # If positive, we're out of credits (bad!)
            credits_used = abs(total_net_cost)
            credits_exhausted = total_net_cost > 0

            # Estimate remaining credits
            # CEREBRO tracks net cost: negative = credits being used
            # We have $10,000 total credits
            TOTAL_CREDITS = 10000.0
            credits_remaining = TOTAL_CREDITS - credits_used

            # Calculate burn rate
            burn_rate_per_day = credits_used / days_back if days_back > 0 else 0

            # Validation logic
            if credits_exhausted:
                return {
                    "approved": False,
                    "reason": f"GCP credits exhausted (used ${credits_used:.2f})",
                    "recommendation": "Switch to spot instances or alternative provider",
                    "credits_remaining": 0,
                    "burn_rate_per_day": burn_rate_per_day,
                    "days_until_exhausted": 0
                }

            if credits_remaining < estimated_cost:
                return {
                    "approved": False,
                    "reason": f"Insufficient credits (need ${estimated_cost:.2f}, have ${credits_remaining:.2f})",
                    "recommendation": "Reduce max_trials or use smaller batch sizes",
                    "credits_remaining": credits_remaining,
                    "burn_rate_per_day": burn_rate_per_day,
                    "days_until_exhausted": credits_remaining / burn_rate_per_day if burn_rate_per_day > 0 else float('inf')
                }

            # Low credit warning (< 10% remaining)
            if credits_remaining < TOTAL_CREDITS * 0.1:
                recommendation = f"⚠️  Low credits ({credits_remaining:.2f} / ${TOTAL_CREDITS:.0f}). Plan accordingly."
            else:
                recommendation = f"✅ Credits healthy ({credits_remaining:.2f} / ${TOTAL_CREDITS:.0f})"

            days_until_exhausted = credits_remaining / burn_rate_per_day if burn_rate_per_day > 0 else float('inf')

            return {
                "approved": True,
                "credits_remaining": credits_remaining,
                "credits_used": credits_used,
                "burn_rate_per_day": burn_rate_per_day,
                "days_until_exhausted": days_until_exhausted,
                "recommendation": recommendation,
                "total_credits": TOTAL_CREDITS,
                "percentage_remaining": (credits_remaining / TOTAL_CREDITS) * 100
            }

        except Exception as e:
            print(f"⚠️  Credit validation error: {e}")
            # Fail open - allow run even if validation fails
            return {
                "approved": True,
                "reason": f"Validation error: {e}",
                "credits_remaining": float('inf')
            }

    def get_credit_status(self, days_back: int = 7) -> Dict:
        """
        Get current credit status (non-blocking query)

        Args:
            days_back: Days to analyze

        Returns:
            Detailed credit status report
        """

        if not self.auditor:
            return {"error": "CEREBRO auditor not available"}

        try:
            status = self.auditor.audit_credit_consumption(days_back=days_back)

            TOTAL_CREDITS = 10000.0
            credits_used = abs(status.get('total_net_cost', 0))
            credits_remaining = TOTAL_CREDITS - credits_used
            burn_rate = credits_used / days_back if days_back > 0 else 0

            return {
                "total_credits": TOTAL_CREDITS,
                "credits_used": credits_used,
                "credits_remaining": credits_remaining,
                "percentage_used": (credits_used / TOTAL_CREDITS) * 100,
                "percentage_remaining": (credits_remaining / TOTAL_CREDITS) * 100,
                "burn_rate_per_day": burn_rate,
                "days_until_exhausted": credits_remaining / burn_rate if burn_rate > 0 else float('inf'),
                "analysis_period_days": days_back,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            return {"error": str(e)}

    def forecast_credit_exhaustion(
        self,
        planned_experiments: List[Dict]
    ) -> Dict:
        """
        Forecast when credits will be exhausted given planned experiments

        Args:
            planned_experiments: List of dicts with:
                - name: str
                - estimated_cost: float
                - estimated_duration_days: float

        Returns:
            Forecast with timeline and warnings
        """

        current_status = self.get_credit_status(days_back=7)

        if "error" in current_status:
            return current_status

        credits_remaining = current_status["credits_remaining"]
        baseline_burn_rate = current_status["burn_rate_per_day"]

        # Simulate timeline
        timeline = []
        current_credits = credits_remaining
        current_day = 0

        for exp in planned_experiments:
            exp_cost = exp.get("estimated_cost", 0)
            exp_days = exp.get("estimated_duration_days", 1)
            daily_cost = exp_cost / exp_days

            # Simulate each day of experiment
            for day in range(int(exp_days)):
                current_day += 1
                current_credits -= daily_cost
                current_credits -= baseline_burn_rate  # Background usage

                timeline.append({
                    "day": current_day,
                    "experiment": exp.get("name", "unknown"),
                    "credits_remaining": current_credits,
                    "daily_cost": daily_cost + baseline_burn_rate
                })

                if current_credits <= 0:
                    break

            if current_credits <= 0:
                break

        # Find exhaustion point
        exhaustion_day = next(
            (t["day"] for t in timeline if t["credits_remaining"] <= 0),
            None
        )

        return {
            "current_credits": credits_remaining,
            "planned_experiments": len(planned_experiments),
            "total_planned_cost": sum(e.get("estimated_cost", 0) for e in planned_experiments),
            "exhaustion_day": exhaustion_day,
            "credits_at_completion": timeline[-1]["credits_remaining"] if timeline else credits_remaining,
            "sufficient_credits": exhaustion_day is None,
            "timeline": timeline,
            "recommendation": (
                "✅ Sufficient credits for all planned experiments"
                if exhaustion_day is None
                else f"⚠️  Credits exhausted at day {exhaustion_day}. Reduce scope or add credits."
            )
        }


if __name__ == "__main__":
    main()
