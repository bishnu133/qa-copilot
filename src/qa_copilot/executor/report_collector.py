import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging
from jinja2 import Template

logger = logging.getLogger(__name__)


class ReportCollector:
    """Collects and generates test execution reports"""

    def __init__(self, output_dir: str = "test-results"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

    def generate_report(self, results: Dict[str, Any], format: str = "html") -> str:
        """
        Generate test report in specified format

        Args:
            results: Test execution results
            format: Report format (html, json, junit)

        Returns:
            Path to generated report
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if format == "html":
            return self._generate_html_report(results, timestamp)
        elif format == "json":
            return self._generate_json_report(results, timestamp)
        elif format == "junit":
            return self._generate_junit_report(results, timestamp)
        else:
            raise ValueError(f"Unsupported report format: {format}")

    def _generate_html_report(self, results: Dict[str, Any], timestamp: str) -> str:
        """Generate HTML report"""
        html_template = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Test Execution Report - {{ timestamp }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background-color: #f5f5f5;
        }
        .header {
            background-color: #333;
            color: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .summary {
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
        }
        .summary-card {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            flex: 1;
            text-align: center;
        }
        .summary-card h3 {
            margin: 0 0 10px 0;
            color: #666;
        }
        .summary-card .number {
            font-size: 36px;
            font-weight: bold;
        }
        .passed { color: #28a745; }
        .failed { color: #dc3545; }
        .skipped { color: #ffc107; }
        .feature {
            background: white;
            margin-bottom: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .feature-header {
            background: #f8f9fa;
            padding: 15px 20px;
            border-bottom: 1px solid #dee2e6;
            cursor: pointer;
        }
        .feature-header.passed {
            border-left: 5px solid #28a745;
        }
        .feature-header.failed {
            border-left: 5px solid #dc3545;
        }
        .scenario {
            padding: 15px 20px;
            border-bottom: 1px solid #eee;
        }
        .scenario:last-child {
            border-bottom: none;
        }
        .scenario-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .scenario-name {
            font-weight: bold;
        }
        .status-badge {
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            color: white;
        }
        .status-badge.passed {
            background-color: #28a745;
        }
        .status-badge.failed {
            background-color: #dc3545;
        }
        .step {
            margin-left: 20px;
            padding: 5px 0;
            font-family: monospace;
            font-size: 14px;
        }
        .step.passed::before {
            content: "✓ ";
            color: #28a745;
        }
        .step.failed::before {
            content: "✗ ";
            color: #dc3545;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            padding: 10px;
            margin: 10px 0 10px 20px;
            border-radius: 3px;
            font-size: 12px;
        }
        .tags {
            display: flex;
            gap: 5px;
            margin-top: 5px;
        }
        .tag {
            background-color: #e9ecef;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 11px;
            color: #495057;
        }
        .duration {
            color: #6c757d;
            font-size: 12px;
        }
    </style>
    <script>
        function toggleFeature(featureId) {
            const content = document.getElementById(featureId);
            content.style.display = content.style.display === 'none' ? 'block' : 'none';
        }
    </script>
</head>
<body>
    <div class="header">
        <h1>Test Execution Report</h1>
        <p>Generated: {{ timestamp }}</p>
        <p>Duration: {{ duration }}</p>
    </div>

    <div class="summary">
        <div class="summary-card">
            <h3>Total Features</h3>
            <div class="number">{{ summary.total }}</div>
        </div>
        <div class="summary-card">
            <h3>Passed</h3>
            <div class="number passed">{{ summary.passed }}</div>
        </div>
        <div class="summary-card">
            <h3>Failed</h3>
            <div class="number failed">{{ summary.failed }}</div>
        </div>
        <div class="summary-card">
            <h3>Pass Rate</h3>
            <div class="number">{{ pass_rate }}%</div>
        </div>
    </div>

    {% for feature in features %}
    <div class="feature">
        <div class="feature-header {{ feature.status }}" onclick="toggleFeature('feature-{{ loop.index }}')">
            <h2>{{ feature.feature }}</h2>
            <div class="duration">{{ feature.file }}</div>
        </div>
        <div id="feature-{{ loop.index }}" class="feature-content">
            {% for scenario in feature.scenarios %}
            <div class="scenario">
                <div class="scenario-header">
                    <div>
                        <div class="scenario-name">{{ scenario.name }}</div>
                        {% if scenario.tags %}
                        <div class="tags">
                            {% for tag in scenario.tags %}
                            <span class="tag">{{ tag }}</span>
                            {% endfor %}
                        </div>
                        {% endif %}
                    </div>
                    <span class="status-badge {{ scenario.status }}">{{ scenario.status|upper }}</span>
                </div>

                {% for step in scenario.steps %}
                <div class="step {{ step.status }}">
                    {{ step.keyword }} {{ step.name }}
                </div>
                {% if step.error %}
                <div class="error">{{ step.error }}</div>
                {% endif %}
                {% endfor %}
            </div>
            {% endfor %}
        </div>
    </div>
    {% endfor %}
</body>
</html>
        """

        # Calculate additional metrics
        summary = results.get('summary', {})
        total = summary.get('total', 0)
        passed = summary.get('passed', 0)
        pass_rate = round((passed / total * 100) if total > 0 else 0, 1)

        # Calculate duration
        start_time = datetime.fromisoformat(results.get('start_time', datetime.now().isoformat()))
        end_time = datetime.fromisoformat(results.get('end_time', datetime.now().isoformat()))
        duration = str(end_time - start_time)

        # Render template
        template = Template(html_template)
        html_content = template.render(
            timestamp=timestamp,
            duration=duration,
            summary=summary,
            pass_rate=pass_rate,
            features=results.get('features', [])
        )

        # Save report
        report_path = self.output_dir / f"report_{timestamp}.html"
        with open(report_path, 'w') as f:
            f.write(html_content)

        logger.info(f"HTML report generated: {report_path}")
        return str(report_path)

    def _generate_json_report(self, results: Dict[str, Any], timestamp: str) -> str:
        """Generate JSON report"""
        report_path = self.output_dir / f"report_{timestamp}.json"

        with open(report_path, 'w') as f:
            json.dump(results, f, indent=2)

        logger.info(f"JSON report generated: {report_path}")
        return str(report_path)

    def _generate_junit_report(self, results: Dict[str, Any], timestamp: str) -> str:
        """Generate JUnit XML report"""
        junit_template = """<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="QA-Copilot Test Results" time="{{ duration }}" tests="{{ total_tests }}" failures="{{ failures }}">
    {% for feature in features %}
    <testsuite name="{{ feature.feature }}" tests="{{ feature.scenarios|length }}" failures="{{ feature.failures }}" time="{{ feature.duration }}">
        {% for scenario in feature.scenarios %}
        <testcase classname="{{ feature.feature|replace(' ', '_') }}" name="{{ scenario.name }}" time="{{ scenario.duration }}">
            {% if scenario.status == 'failed' %}
            <failure message="{{ scenario.error|default('Test failed') }}">
                {% for step in scenario.steps %}
                {% if step.status == 'failed' %}
                {{ step.keyword }} {{ step.name }}
                Error: {{ step.error }}
                {% endif %}
                {% endfor %}
            </failure>
            {% endif %}
        </testcase>
        {% endfor %}
    </testsuite>
    {% endfor %}
</testsuites>
        """

        # Prepare data for JUnit format
        total_tests = sum(len(f.get('scenarios', [])) for f in results.get('features', []))
        failures = sum(1 for f in results.get('features', [])
                       for s in f.get('scenarios', [])
                       if s.get('status') == 'failed')

        # Calculate durations
        for feature in results.get('features', []):
            feature['failures'] = sum(1 for s in feature.get('scenarios', [])
                                      if s.get('status') == 'failed')

            # Calculate feature duration
            if feature.get('start_time') and feature.get('end_time'):
                start = datetime.fromisoformat(feature['start_time'])
                end = datetime.fromisoformat(feature['end_time'])
                feature['duration'] = (end - start).total_seconds()
            else:
                feature['duration'] = 0

            # Calculate scenario durations
            for scenario in feature.get('scenarios', []):
                if scenario.get('start_time') and scenario.get('end_time'):
                    start = datetime.fromisoformat(scenario['start_time'])
                    end = datetime.fromisoformat(scenario['end_time'])
                    scenario['duration'] = (end - start).total_seconds()
                else:
                    scenario['duration'] = 0

        # Overall duration
        if results.get('start_time') and results.get('end_time'):
            start = datetime.fromisoformat(results['start_time'])
            end = datetime.fromisoformat(results['end_time'])
            duration = (end - start).total_seconds()
        else:
            duration = 0

        # Render template
        template = Template(junit_template)
        junit_content = template.render(
            duration=duration,
            total_tests=total_tests,
            failures=failures,
            features=results.get('features', [])
        )

        # Save report
        report_path = self.output_dir / f"report_{timestamp}.xml"
        with open(report_path, 'w') as f:
            f.write(junit_content)

        logger.info(f"JUnit report generated: {report_path}")
        return str(report_path)

    def generate_allure_report(self, results: Dict[str, Any]):
        """Generate Allure report data"""
        # This would integrate with Allure reporting framework
        # Placeholder for future implementation
        pass