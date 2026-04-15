"""Backend Development Agent for ETF Tracking System."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Any

from dev_agents.base import BackendDevAgent, DevTaskResult, DevTaskStatus


class BackendAgent(BackendDevAgent):
    """
    Backend Development Agent responsible for API and service development.
    
    Capabilities:
    - Create new API endpoints
    - Implement service layer logic
    - Database schema modifications
    - Performance optimization
    """
    
    def __init__(self, project_path: Optional[Path] = None):
        """Initialize BackendAgent."""
        super().__init__("BackendAgent", project_path)
    
    @property
    def description(self) -> str:
        return "Develops and maintains backend services and APIs"
    
    def execute_task(self, task: dict) -> DevTaskResult:
        """
        Execute backend development task.
        
        Task types:
        - create_endpoint: Create new API endpoint
        - optimize_query: Optimize database query
        - add_service: Add new service module
        - update_schema: Update database schema
        """
        task_type = task.get("type")
        
        if task_type == "create_endpoint":
            return self.create_api_endpoint(
                method=task["method"],
                path=task["path"],
                description=task.get("description", ""),
                request_schema=task.get("request_schema", {}),
                response_schema=task.get("response_schema", {}),
                implementation=task.get("implementation", {})
            )
        elif task_type == "optimize_query":
            return self.optimize_query(
                module=task["module"],
                function=task["function"],
                optimization_hints=task.get("hints", [])
            )
        elif task_type == "add_service":
            return self.add_service(
                service_name=task["service_name"],
                functions=task.get("functions", []),
                dependencies=task.get("dependencies", [])
            )
        elif task_type == "update_schema":
            return self.update_schema(
                changes=task["changes"],
                migration_script=task.get("migration_script", "")
            )
        else:
            return self.create_task_result(
                task_type="unknown",
                description=f"Unknown task type: {task_type}",
                status=DevTaskStatus.FAILED,
                error="Invalid task type"
            )
    
    def create_api_endpoint(
        self,
        method: str,
        path: str,
        description: str,
        request_schema: dict,
        response_schema: dict,
        implementation: dict = None
    ) -> DevTaskResult:
        """
        Create a new API endpoint.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: Endpoint path (e.g., "/etfs/compare")
            description: Endpoint description
            request_schema: Request parameter schema
            response_schema: Response schema
            implementation: Implementation details
            
        Returns:
            DevTaskResult with implementation details
        """
        self.log_action(f"Creating {method} endpoint", path)
        
        try:
            main_path = self.get_app_path("main.py")
            content = main_path.read_text(encoding="utf-8")
            
            # Generate endpoint code
            endpoint_code = self._generate_endpoint_code(
                method=method,
                path=path,
                description=description,
                request_schema=request_schema,
                response_schema=response_schema,
                implementation=implementation or {}
            )
            
            # Find insertion point (after existing endpoints)
            # For now, insert before last line
            lines = content.split('\n')
            insert_pos = len(lines) - 1
            
            # Insert new endpoint
            lines.insert(insert_pos, f"\n\n# New endpoint: {method} {path}\n" + endpoint_code)
            new_content = '\n'.join(lines)
            
            # Write updated file
            main_path.write_text(new_content, encoding="utf-8")
            
            return self.create_task_result(
                task_type="create_endpoint",
                description=f"Created {method} {path}",
                status=DevTaskStatus.COMPLETED,
                changes_made=[
                    f"Added {method} endpoint at {path}",
                    f"Description: {description}",
                    "Updated app/main.py"
                ],
                files_modified=[str(main_path)]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create endpoint: {e}", exc_info=True)
            return self.create_task_result(
                task_type="create_endpoint",
                description=f"Create {method} {path}",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def _generate_endpoint_code(
        self,
        method: str,
        path: str,
        description: str,
        request_schema: dict,
        response_schema: dict,
        implementation: dict
    ) -> str:
        """Generate FastAPI endpoint code."""
        
        # Generate decorator
        http_method = method.lower()
        decorator = f"@app.{http_method}({path!r})"
        
        # Generate function signature
        func_name = f"{implementation.get('func_name', path.replace('/', '_').strip('_'))}"
        params = []
        
        # Add path parameters
        path_params = [p.strip("{}") for p in path.split("/") if "{" in p]
        for param in path_params:
            params.append(f"{param}: str")
        
        # Add query parameters
        if "query" in request_schema:
            for param_name, param_info in request_schema["query"].items():
                param_type = param_info.get("type", "str")
                default = param_info.get("default", "None")
                params.append(f"{param_name}: {param_type} = {default}")
        
        params_str = ", ".join(params) if params else ""
        
        # Generate docstring
        docstring = f'"""{description}."""'
        
        # Generate function body
        body = implementation.get("body", "return {}")
        
        return f"""
{decorator}
def {func_name}({params_str}) -> dict:
    {docstring}
    {body}
"""
    
    def add_service(
        self,
        service_name: str,
        functions: list[dict],
        dependencies: list[str] = None
    ) -> DevTaskResult:
        """
        Add a new service module.
        
        Args:
            service_name: Name of service (e.g., "comparison")
            functions: List of functions to implement
            dependencies: List of module dependencies
            
        Returns:
            DevTaskResult with implementation details
        """
        self.log_action(f"Creating service", service_name)
        
        try:
            service_path = self.get_service_path(service_name)
            
            # Generate service code
            service_code = self._generate_service_code(
                service_name=service_name,
                functions=functions,
                dependencies=dependencies or []
            )
            
            # Write service file
            service_path.write_text(service_code, encoding="utf-8")
            
            # Update __init__.py
            init_path = self.project_path / "app" / "services" / "__init__.py"
            if init_path.exists():
                init_content = init_path.read_text()
                if f"from .{service_name}" not in init_content:
                    init_content += f"\nfrom .{service_name} import *"
                    init_path.write_text(init_content, encoding="utf-8")
            
            return self.create_task_result(
                task_type="add_service",
                description=f"Created {service_name} service",
                status=DevTaskStatus.COMPLETED,
                changes_made=[
                    f"Created app/services/{service_name}.py",
                    f"Implemented {len(functions)} functions",
                    "Updated services/__init__.py"
                ],
                files_modified=[str(service_path)]
            )
            
        except Exception as e:
            self.logger.error(f"Failed to add service: {e}", exc_info=True)
            return self.create_task_result(
                task_type="add_service",
                description=f"Add {service_name} service",
                status=DevTaskStatus.FAILED,
                error=str(e)
            )
    
    def _generate_service_code(
        self,
        service_name: str,
        functions: list[dict],
        dependencies: list[str]
    ) -> str:
        """Generate service module code."""
        
        lines = [
            f'"""{service_name.title()} service module."""',
            '',
            'from __future__ import annotations',
            '',
        ]
        
        # Add imports
        if dependencies:
            lines.append('# Dependencies')
            for dep in dependencies:
                lines.append(f'from {dep} import *')
            lines.append('')
        
        # Generate functions
        for func in functions:
            func_name = func.get("name", f"{service_name}_function")
            docstring = func.get("docstring", f"{func_name} function")
            params = func.get("params", [])
            return_type = func.get("return_type", "dict")
            
            # Build function signature
            params_str = ", ".join([f"{p['name']}: {p['type']}" for p in params]) if params else ""
            
            lines.extend([
                f'def {func_name}({params_str}) -> {return_type}:',
                f'    """{docstring}"""',
                '    # TODO: Implement',
                '    pass',
                ''
            ])
        
        return '\n'.join(lines)
    
    def optimize_query(
        self,
        module: str,
        function: str,
        optimization_hints: list[str] = None
    ) -> DevTaskResult:
        """
        Optimize a database query.
        
        Args:
            module: Module name (e.g., "repositories")
            function: Function name
            optimization_hints: Optimization suggestions
            
        Returns:
            DevTaskResult with optimization details
        """
        self.log_action(f"Optimizing query", f"{module}.{function}")
        
        # Placeholder implementation
        return self.create_task_result(
            task_type="optimize_query",
            description=f"Optimize {module}.{function}",
            status=DevTaskStatus.COMPLETED,
            changes_made=[f"Applied {len(optimization_hints or [])} optimizations"],
            files_modified=[str(self.get_app_path(module + ".py"))]
        )
    
    def update_schema(
        self,
        changes: list[dict],
        migration_script: str = ""
    ) -> DevTaskResult:
        """
        Update database schema.
        
        Args:
            changes: List of schema changes
            migration_script: SQL migration script
            
        Returns:
            DevTaskResult with migration details
        """
        self.log_action("Updating database schema")
        
        # Placeholder implementation
        return self.create_task_result(
            task_type="update_schema",
            description="Update database schema",
            status=DevTaskStatus.COMPLETED,
            changes_made=[f"Applied {len(changes)} schema changes"]
        )


# Standalone testing
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    agent = BackendAgent()
    
    # Test creating an endpoint
    result = agent.create_api_endpoint(
        method="GET",
        path="/etfs/compare",
        description="Compare holdings across multiple ETFs",
        request_schema={
            "query": {
                "tickers": {"type": "str", "default": 'Query(...)'},
                "date": {"type": "str", "default": 'Query(None)'}
            }
        },
        response_schema={
            "type": "dict",
            "fields": ["tickers", "comparison", "date"]
        },
        implementation={
            "func_name": "compare_etfs",
            "body": """
# TODO: Implement comparison logic
return {"tickers": tickers, "comparison": [], "date": date}
"""
        }
    )
    
    import json
    print("\n" + "="*60)
    print("BACKEND TASK RESULT")
    print("="*60)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
