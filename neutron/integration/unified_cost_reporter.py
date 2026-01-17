"""
Unified Cost Reporter - Neutron + CEREBRO

Filosofia: One dashboard to rule them all
          Track every dollar across on-prem GPU + GCP credits

Features:
- Aggregate Neutron compute costs (GPU/CPU/storage)
- Aggregate CEREBRO GCP credit usage
- Unified reporting and forecasting
- ROI analysis (cost vs model performance)
"""
import os
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
import json

from neutron.tracking.cost_tracker import CostTracker, CerebroCreditValidator, CostConfig


class UnifiedCostReporter:
    """
    Unified view of all ML infrastructure costs

    Aggregates:
    - Neutron: GPU hours, CPU hours, storage, MLflow overhead
    - CEREBRO: GCP credits ($10K burn target)

    Reports:
    - Total spend across both systems
    - Cost breakdown by source
    - Burn rate and forecast
    - ROI metrics (cost per accuracy point)
    """

    def __init__(
        self,
        mlflow_uri: str = "http://localhost:5000",
        gcp_project_id: str = "gen-lang-client-0530325234",
        cost_config: Optional[CostConfig] = None
    ):
        # Initialize Neutron cost tracker
        self.neutron_tracker = CostTracker(
            mlflow_uri=mlflow_uri,
            cost_config=cost_config or CostConfig()
        )

        # Initialize CEREBRO validator
        self.cerebro_validator = CerebroCreditValidator(
            project_id=gcp_project_id
        )

        self.gcp_project_id = gcp_project_id

    def generate_comprehensive_report(
        self,
        experiment_name: str,
        days_back: int = 7
    ) -> Dict:
        """
        Generate unified cost report for experiment

        Args:
            experiment_name: MLflow experiment name
            days_back: Days to analyze for CEREBRO credit usage

        Returns:
            Comprehensive report with Neutron + CEREBRO costs
        """

        print(f"📊 Generating unified cost report for: {experiment_name}")
        print("")

        # Get Neutron costs
        print("⚙️  Analyzing Neutron costs...")
        neutron_analysis = self.neutron_tracker.analyze_experiment(experiment_name)

        # Get CEREBRO credit status
        print("💳 Checking CEREBRO GCP credits...")
        cerebro_status = self.cerebro_validator.get_credit_status(days_back=days_back)

        # Aggregate costs
        neutron_total = neutron_analysis.get("summary", {}).get("total_cost", 0)
        cerebro_credits_used = cerebro_status.get("credits_used", 0) if "error" not in cerebro_status else 0
        total_cost = neutron_total + cerebro_credits_used

        # Calculate ROI metrics
        best_accuracy = neutron_analysis.get("summary", {}).get("best_accuracy", 0)
        cost_per_accuracy_point = total_cost / (best_accuracy * 100) if best_accuracy > 0 else float('inf')

        # Burn rate analysis
        neutron_burn_rate = neutron_total / days_back if days_back > 0 else 0
        cerebro_burn_rate = cerebro_status.get("burn_rate_per_day", 0) if "error" not in cerebro_status else 0
        total_burn_rate = neutron_burn_rate + cerebro_burn_rate

        # Forecast remaining budget
        cerebro_credits_remaining = cerebro_status.get("credits_remaining", 0) if "error" not in cerebro_status else 10000.0
        days_until_exhausted = cerebro_credits_remaining / total_burn_rate if total_burn_rate > 0 else float('inf')

        report = {
            "experiment": experiment_name,
            "gcp_project": self.gcp_project_id,
            "analysis_period_days": days_back,
            "timestamp": datetime.now().isoformat(),

            # Unified summary
            "unified_summary": {
                "total_cost_all_sources": total_cost,
                "cost_per_accuracy_point": cost_per_accuracy_point,
                "total_burn_rate_per_day": total_burn_rate,
                "days_until_budget_exhausted": days_until_exhausted,
                "budget_health": self._assess_budget_health(cerebro_credits_remaining, total_burn_rate)
            },

            # Neutron costs (on-prem/cloud GPU)
            "neutron": {
                "total_cost": neutron_total,
                "gpu_cost": neutron_analysis.get("cost_breakdown", {}).get("gpu", 0),
                "cpu_cost": neutron_analysis.get("cost_breakdown", {}).get("cpu", 0),
                "storage_cost": neutron_analysis.get("cost_breakdown", {}).get("storage", 0),
                "gpu_hours": neutron_analysis.get("cost_breakdown", {}).get("breakdown", {}).get("gpu_hours", 0),
                "total_runs": neutron_analysis.get("summary", {}).get("total_runs", 0),
                "success_rate": neutron_analysis.get("utilization", {}).get("success_rate", 0),
                "best_accuracy": best_accuracy,
                "burn_rate_per_day": neutron_burn_rate
            },

            # CEREBRO costs (GCP credits)
            "cerebro": {
                "total_credits": cerebro_status.get("total_credits", 10000.0) if "error" not in cerebro_status else 10000.0,
                "credits_used": cerebro_credits_used,
                "credits_remaining": cerebro_credits_remaining,
                "percentage_used": cerebro_status.get("percentage_used", 0) if "error" not in cerebro_status else 0,
                "burn_rate_per_day": cerebro_burn_rate,
                "days_until_exhausted": cerebro_status.get("days_until_exhausted", float('inf')) if "error" not in cerebro_status else float('inf'),
                "status": "healthy" if "error" not in cerebro_status else "error",
                "error": cerebro_status.get("error") if "error" in cerebro_status else None
            },

            # Cost breakdown by source
            "cost_breakdown": {
                "neutron_percentage": (neutron_total / total_cost * 100) if total_cost > 0 else 0,
                "cerebro_percentage": (cerebro_credits_used / total_cost * 100) if total_cost > 0 else 0,
            },

            # Recommendations
            "recommendations": self._generate_unified_recommendations(
                neutron_analysis,
                cerebro_status,
                total_burn_rate,
                days_until_exhausted
            ),

            # Full details (for deep dive)
            "neutron_detailed": neutron_analysis,
            "cerebro_detailed": cerebro_status
        }

        return report

    def _assess_budget_health(
        self,
        credits_remaining: float,
        burn_rate: float
    ) -> str:
        """Assess overall budget health"""

        if credits_remaining <= 0:
            return "🔴 CRITICAL - Credits exhausted"

        days_left = credits_remaining / burn_rate if burn_rate > 0 else float('inf')

        if days_left < 7:
            return f"🟠 WARNING - {days_left:.1f} days remaining"
        elif days_left < 30:
            return f"🟡 CAUTION - {days_left:.1f} days remaining"
        else:
            return f"🟢 HEALTHY - {days_left:.0f}+ days remaining"

    def _generate_unified_recommendations(
        self,
        neutron_analysis: Dict,
        cerebro_status: Dict,
        total_burn_rate: float,
        days_until_exhausted: float
    ) -> list:
        """Generate unified optimization recommendations"""

        recommendations = []

        # Get Neutron recommendations
        neutron_recs = neutron_analysis.get("recommendations", [])
        recommendations.extend([f"[Neutron] {rec}" for rec in neutron_recs])

        # CEREBRO-specific recommendations
        if "error" not in cerebro_status:
            credits_remaining = cerebro_status.get("credits_remaining", 0)
            percentage_remaining = cerebro_status.get("percentage_remaining", 0)

            if percentage_remaining < 10:
                recommendations.append(
                    f"[CEREBRO] 🔴 CRITICAL: Only {percentage_remaining:.1f}% credits remaining. "
                    f"Reduce workload immediately or risk service interruption."
                )
            elif percentage_remaining < 25:
                recommendations.append(
                    f"[CEREBRO] ⚠️  WARNING: {percentage_remaining:.1f}% credits remaining. "
                    f"Plan to complete experiments within {days_until_exhausted:.0f} days."
                )

            if total_burn_rate > 150:  # $150/day
                recommendations.append(
                    f"[Unified] 💰 High burn rate (${total_burn_rate:.2f}/day). "
                    f"At this rate, budget exhausted in {days_until_exhausted:.0f} days. "
                    f"Consider: (1) Reduce parallel trials, (2) Use spot instances, (3) Optimize batch sizes."
                )

        # ROI recommendations
        neutron_total = neutron_analysis.get("summary", {}).get("total_cost", 0)
        best_accuracy = neutron_analysis.get("summary", {}).get("best_accuracy", 0)

        if best_accuracy > 0:
            cost_per_point = neutron_total / (best_accuracy * 100)
            if cost_per_point > 1.0:
                recommendations.append(
                    f"[ROI] 📉 High cost per accuracy point (${cost_per_point:.2f}). "
                    f"Consider early stopping or more aggressive hyperparameter pruning."
                )

        return recommendations

    def export_unified_report(
        self,
        experiment_name: str,
        output_file: str = "unified_cost_report.json",
        days_back: int = 7
    ) -> Dict:
        """Export unified report to file"""

        report = self.generate_comprehensive_report(experiment_name, days_back)

        # Pretty print summary first
        self.print_summary(report)

        # Export full report
        Path(output_file).write_text(json.dumps(report, indent=2, default=str))
        print(f"\n📄 Full report exported to: {output_file}")

        return report

    def print_summary(self, report: Dict):
        """Pretty print report summary"""

        print("\n" + "="*80)
        print(f"  📊 Unified Cost Report: {report['experiment']}")
        print("="*80)

        # Unified summary
        summary = report["unified_summary"]
        print(f"\n💰 Total Cost (All Sources): ${summary['total_cost_all_sources']:.2f}")
        print(f"🎯 Cost per Accuracy Point: ${summary['cost_per_accuracy_point']:.3f}")
        print(f"🔥 Daily Burn Rate: ${summary['total_burn_rate_per_day']:.2f}/day")
        print(f"⏳ Budget Status: {summary['budget_health']}")

        # Breakdown
        print(f"\n📦 Cost Breakdown:")
        neutron = report["neutron"]
        cerebro = report["cerebro"]
        print(f"  Neutron (GPU/CPU):  ${neutron['total_cost']:.2f} ({report['cost_breakdown']['neutron_percentage']:.1f}%)")
        print(f"    • GPU Hours: {neutron['gpu_hours']:.1f}h")
        print(f"    • Success Rate: {neutron['success_rate']:.1%}")
        print(f"    • Best Accuracy: {neutron['best_accuracy']:.4f}")

        print(f"\n  CEREBRO (GCP):      ${cerebro['credits_used']:.2f} ({report['cost_breakdown']['cerebro_percentage']:.1f}%)")
        print(f"    • Credits Remaining: ${cerebro['credits_remaining']:.2f} / ${cerebro['total_credits']:.2f}")
        print(f"    • Credits Used: {cerebro['percentage_used']:.1f}%")
        print(f"    • Days Until Exhausted: {cerebro['days_until_exhausted']:.0f}" if cerebro['days_until_exhausted'] != float('inf') else "    • Days Until Exhausted: ∞")

        # Recommendations
        if report["recommendations"]:
            print(f"\n💡 Recommendations:")
            for rec in report["recommendations"]:
                print(f"  • {rec}")

        print("\n" + "="*80)


def main():
    """CLI interface for unified cost reporting"""
    import argparse

    parser = argparse.ArgumentParser(description="Unified Cost Reporter - Neutron + CEREBRO")
    parser.add_argument("experiment", help="Experiment name")
    parser.add_argument("--days", "-d", type=int, default=7, help="Days to analyze")
    parser.add_argument("--output", "-o", default="unified_cost_report.json", help="Output file")
    parser.add_argument("--gcp-project", "-p", default="gen-lang-client-0530325234", help="GCP project ID")

    args = parser.parse_args()

    reporter = UnifiedCostReporter(gcp_project_id=args.gcp_project)
    reporter.export_unified_report(
        args.experiment,
        output_file=args.output,
        days_back=args.days
    )


if __name__ == "__main__":
    main()
