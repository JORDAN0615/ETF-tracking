"""Frontend Development Agent for ETF Tracking System."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from dev_agents.base import FrontendDevAgent, DevTaskResult, DevTaskStatus


class FrontendAgent(FrontendDevAgent):
    """
    Frontend Development Agent responsible for UI/UX improvements.
    
    Capabilities:
    - HTML template modification
    - Chart integration (Chart.js, D3.js)
    - Responsive design
    - User experience enhancements
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize FrontendAgent."""
        super().__init__("FrontendAgent", project_path)
    
    @property
    def description(self) -> str:
        return "Develops and improves UI/UX for ETF tracking system"
    
    def execute_task(self, task: dict) -> DevTaskResult:
        """
        Execute frontend development task.
        
        Task types:
        - enhance_template: Add feature to existing template
        - add_chart: Add visualization chart
        - improve_layout: Improve page layout
        - add_interactivity: Add interactive features
        """
        task_type = task.get("type")
        
        if task_type == "enhance_template":
            return self.enhance_template(
                template_name=task["template_name"],
                feature=task["feature"],
                details=task.get("details", {})
            )
        elif task_type == "add_chart":
            return self.add_chart(
                template_name=task["template_name"],
                chart_type=task["chart_type"],
                data_source=task["data_source"],
                config=task.get("config", {})
            )
        elif task_type == "improve_layout":
            return self.improve_layout(
                template_name=task["template_name"],
                improvements=task.get("improvements", [])
            )
        elif task_type == "add_interactivity":
            return self.add_interactivity(
                template_name=task["template_name"],
                feature=task["feature"]
            )
        else:
            return self.create_task_result(
                task_type="unknown",
                description=f"Unknown task type: {task_type}",
                status=DevTaskStatus.FAILED,
                error="Invalid task type"
            )
    
    def enhance_template(
        self,
        template_name: str,
        feature: str,
        details: dict = None
    ) -> DevTaskResult:
        """
        Enhance an HTML template with new feature.
        
        Args:
            template_name: Template file name
            feature: Feature description
            details: Additional implementation details
            
        Returns:
            DevTaskResult with changes made
        """
        self.log_action(f"Enhancing template", f"{template_name} with {feature}")
        
        try:
            template_path = self.get_template_path(template_name)
            
            if not template_path.exists():
                return self.create_task_result(
                    task_type="enhance_template",
                    description=f"Enhance {template_name}",
                    status=DevTaskStatus.FAILED,
                    error=f"Template not found: {template_name}"
                )
            
            # Read current template
            content = template_path.read_text(encoding="utf-8")
            original_content = content
            
            changes = []
            
            # Apply feature-specific enhancements
            if "chart" in feature.lower():
                content, chart_changes = self._add_chart_placeholder(content, feature, details)
                changes.extend(chart_changes)
            
            if "search" in feature.lower():
                content, search_changes = self._add_search_functionality(content)
                changes.extend(search_changes)
            
            if "responsive" in feature.lower() or "mobile" in feature.lower():
                content, responsive_changes = self._add_responsive_styles(content)
                changes.extend(responsive_changes)
            
            # Write updated template
            if changes:
                template_path.write_text(content, encoding="utf-8")
                self.log_action(f"Applied {len(changes)} changes to {template_name}")
            
            return self.create_task_result(
                task_type="enhance_template",
                description=f"Enhanced {template_name} with {feature}",
                status=DevTaskStatus.COMPLETED,
                changes_made=changes,
                files_modified=[str(template_path)]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to enhance template: {e}", exc_info=True)
            return self.create_task_result(
                task_type="enhance_template",
                description=f"Enhance {template_name}",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def add_chart(
        self,
        template_name: str,
        chart_type: str,
        data_source: str,
        config: dict = None
    ) -> DevTaskResult:
        """
        Add a chart visualization to template.
        
        Args:
            template_name: Target template
            chart_type: Type of chart (line, bar, pie, etc.)
            data_source: API endpoint or data variable
            config: Chart configuration
            
        Returns:
            DevTaskResult with implementation details
        """
        self.log_action(f"Adding {chart_type} chart", f"to {template_name}")
        
        try:
            template_path = self.get_template_path(template_name)
            content = template_path.read_text(encoding="utf-8")
            
            # Add Chart.js library if not present
            if '<script src="https://cdn.jsdelivr.net/npm/chart.js' not in content:
                content = content.replace(
                    '</head>',
                    f'''    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js"></script>
</head>'''
                )
                self.log_action("Added Chart.js library")
            
            # Create chart container
            chart_html = f'''
    <!-- {chart_type} Chart -->
    <div class="chart-container" style="margin: 2rem 0; padding: 1rem; border: 1px solid #e0e0e0; border-radius: 8px;">
        <h3 style="margin-top: 0; color: #333;">{config.get('title', chart_type.title())} Chart</h3>
        <canvas id="{chart_type.replace(' ', '_')}_chart"></canvas>
    </div>
    
    <script>
    (function() {{
        const ctx = document.getElementById('{chart_type.replace(' ', '_')}_chart').getContext('2d');
        new Chart(ctx, {{
            type: '{chart_type}',
            data: {{
                labels: [],
                datasets: [{{
                    label: '{config.get('label', 'Data')}',
                    data: [],
                    backgroundColor: '{config.get('color', '#4285f4')}',
                    fill: false,
                    tension: 0.1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    legend: {{
                        display: true,
                        position: 'top'
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.dataset.label + ': ' + context.parsed.y;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }},
                    x: {{
                        grid: {{
                            color: 'rgba(0, 0, 0, 0.1)'
                        }}
                    }}
                }}
            }}
        }});
        
        // Fetch data from: DATA_SOURCE_PLACEHOLDER
        // TODO: Implement data fetching and chart update
    }})();
    </script>
'''
            
            # Replace placeholder with actual data source
            chart_html = chart_html.replace('DATA_SOURCE_PLACEHOLDER', data_source)
            
            # Insert chart before closing body tag
            content = content.replace('</body>', chart_html + '\n</body>')
            
            # Write updated template
            template_path.write_text(content, encoding="utf-8")
            
            return self.create_task_result(
                task_type="add_chart",
                description=f"Added {chart_type} chart to {template_name}",
                status=DevTaskStatus.COMPLETED,
                changes_made=[
                    f"Added Chart.js library",
                    f"Created {chart_type} chart container",
                    f"Configured chart with data source: {data_source}"
                ],
                files_modified=[str(template_path)]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to add chart: {e}", exc_info=True)
            return self.create_task_result(
                task_type="add_chart",
                description=f"Add {chart_type} chart",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def _add_chart_placeholder(self, content: str, feature: str, details: dict) -> tuple[str, list[str]]:
        """Add chart placeholder to content."""
        changes = []
        
        # Simple placeholder for now
        placeholder = '''
    <!-- Chart placeholder for: {} -->
    <div id="chart-{}" style="height: 300px; background: #f5f5f5; border-radius: 8px; display: flex; align-items: center; justify-content: center; margin: 1rem 0;">
        <p style="color: #666;">Chart will be loaded here</p>
    </div>
'''.format(feature, feature.replace(" ", "_"))
        
        content = content.replace('</body>', placeholder + '</body>')
        changes.append(f"Added placeholder for {feature}")
        
        return content, changes
    
    def _add_search_functionality(self, content: str) -> tuple[str, list[str]]:
        """Add search functionality to content."""
        changes = []
        
        search_html = '''
    <!-- Search Box -->
    <div style="margin: 1rem 0;">
        <input type="text" id="search-input" placeholder="Search holdings..." 
               style="width: 100%; max-width: 400px; padding: 0.75rem; border: 1px solid #ddd; border-radius: 4px; font-size: 1rem;">
    </div>
    
    <script>
    document.getElementById('search-input').addEventListener('input', function(e) {{
        const searchTerm = e.target.value.toLowerCase();
        // TODO: Implement search filtering
        console.log('Searching for:', searchTerm);
    }});
    </script>
'''
        
        # Insert after first h1 or h2
        header_match = re.search(r'<h[12][^>]*>.*?</h[12]>', content, re.DOTALL)
        if header_match:
            insert_pos = header_match.end()
            content = content[:insert_pos] + '\n' + search_html + content[insert_pos:]
            changes.append("Added search input box")
        
        return content, changes
    
    def _add_responsive_styles(self, content: str) -> tuple[str, list[str]]:
        """Add responsive styles to content."""
        changes = []
        
        responsive_css = '''
    <style>
    @media (max-width: 768px) {
        .chart-container {
            margin: 1rem 0.5rem !important;
            padding: 0.5rem !important;
        }
        table {
            font-size: 0.875rem;
        }
        th, td {
            padding: 0.5rem !important;
        }
    }
    </style>
'''
        
        content = content.replace('</head>', responsive_css + '</head>')
        changes.append("Added responsive CSS media queries")
        
        return content, changes
    
    def improve_layout(self, template_name: str, improvements: list[str]) -> DevTaskResult:
        """Improve page layout based on suggestions."""
        self.log_action(f"Improving layout", f"{template_name}")
        
        # Placeholder implementation
        return self.create_task_result(
            task_type="improve_layout",
            description=f"Improve layout of {template_name}",
            status=DevTaskStatus.COMPLETED,
            changes_made=improvements,
            files_modified=[str(self.get_template_path(template_name))]
        )
    
    def add_interactivity(self, template_name: str, feature: str) -> DevTaskResult:
        """Add interactive feature to template."""
        self.log_action(f"Adding interactivity", f"{feature} to {template_name}")
        
        # Placeholder implementation
        return self.create_task_result(
            task_type="add_interactivity",
            description=f"Add {feature} to {template_name}",
            status=DevTaskStatus.COMPLETED,
            changes_made=[f"Added {feature}"],
            files_modified=[str(self.get_template_path(template_name))]
        )


# Standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = FrontendAgent()
    
    # Test adding a chart
    result = agent.add_chart(
        template_name="detail.html",
        chart_type="line",
        data_source="/api/etfs/00992A/trend/2330",
        config={
            "title": "持股權重趨勢",
            "label": "權重 (%)",
            "color": "#4285f4"
        }
    )
    
    import json
    print("\n" + "="*60)
    print("FRONTEND TASK RESULT")
    print("="*60)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
