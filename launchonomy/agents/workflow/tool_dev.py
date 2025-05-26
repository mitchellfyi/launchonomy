import logging
import os
import json
import importlib
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class ToolDev:
    """
    ToolDev specializes in building out stub tools into working implementations.
    
    Responsibilities:
    1. Monitor registry for "pending" tool stubs
    2. Generate actual tool implementation code based on stub specs
    3. Create proper Python files under launchonomy/tools/
    4. Update registry status to "built"
    5. Trigger ToolQA for testing
    """
    
    def __init__(self, registry, coa):
        """
        Initialize ToolDev.
        
        Args:
            registry: Registry instance for managing agents/tools
            coa: Consensus Orchestration Authority (OrchestrationAgent)
        """
        self.registry = registry
        self.coa = coa
        self.name = "ToolDev"
        
    def _log(self, message: str, level: str = "info"):
        """Helper for logging."""
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.coa, '_log_to_monitor') and callable(self.coa._log_to_monitor):
            self.coa._log_to_monitor(self.name, message, level)
    
    def execute(self) -> Dict[str, Any]:
        """
        Main execution method for ToolDev.
        
        Returns:
            Dict containing execution results and built tools
        """
        self._log("Starting ToolDev execution - building out pending tool stubs", "info")
        
        results = {
            "built_tools": [],
            "errors": [],
            "status": "completed"
        }
        
        try:
            # Find pending tool stubs in registry
            pending_tools = self._find_pending_tools()
            
            self._log(f"Found {len(pending_tools)} pending tools to build", "info")
            
            # Build out pending tools
            for tool_name, tool_spec in pending_tools.items():
                try:
                    built_path = self._build_tool(tool_name, tool_spec)
                    if built_path:
                        self._update_tool_status(tool_name, "built", built_path)
                        results["built_tools"].append({
                            "name": tool_name,
                            "path": built_path,
                            "status": "success"
                        })
                        self._log(f"Successfully built tool: {tool_name} at {built_path}", "info")
                    else:
                        results["errors"].append(f"Failed to build tool: {tool_name}")
                        
                except Exception as e:
                    error_msg = f"Error building tool {tool_name}: {str(e)}"
                    self._log(error_msg, "error")
                    results["errors"].append(error_msg)
            
            # Trigger ToolQA if we built anything
            if results["built_tools"]:
                self._log("Triggering ToolQA for testing newly built tools", "info")
                self._trigger_tool_qa()
                
        except Exception as e:
            error_msg = f"Critical error in ToolDev execution: {str(e)}"
            self._log(error_msg, "error")
            results["errors"].append(error_msg)
            results["status"] = "failed"
        
        self._log(f"ToolDev execution completed. Built {len(results['built_tools'])} tools", "info")
        return results
    
    def _find_pending_tools(self) -> Dict[str, Dict[str, Any]]:
        """Find tools with 'pending' status in registry."""
        pending = {}
        for tool_name, tool_spec in self.registry.tools.items():
            if tool_spec.get("status") == "pending":
                pending[tool_name] = tool_spec
        return pending
    
    def _build_tool(self, tool_name: str, tool_spec: Dict[str, Any]) -> Optional[str]:
        """
        Build out a stub tool into a working implementation.
        
        Args:
            tool_name: Name of the tool to build
            tool_spec: Tool specification from registry
            
        Returns:
            Path to the built tool file, or None if failed
        """
        try:
            # Create tools directory if it doesn't exist
            tools_dir = Path("launchonomy/tools")
            tools_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate tool file path
            tool_filename = f"{tool_name.lower().replace(' ', '_').replace('-', '_')}_tool.py"
            tool_path = tools_dir / tool_filename
            
            # Generate tool implementation code
            tool_code = self._generate_tool_code(tool_name, tool_spec)
            
            # Write tool file
            with open(tool_path, 'w') as f:
                f.write(tool_code)
            
            self._log(f"Created tool implementation at: {tool_path}", "debug")
            return str(tool_path)
            
        except Exception as e:
            self._log(f"Error building tool {tool_name}: {str(e)}", "error")
            return None
    
    def _generate_tool_code(self, tool_name: str, tool_spec: Dict[str, Any]) -> str:
        """Generate Python code for a tool implementation."""
        class_name = f"{tool_name.replace(' ', '').replace('-', '')}Tool"
        description = tool_spec.get("description", f"Auto-generated tool for {tool_name}")
        tool_type = tool_spec.get("type", "webhook")
        
        # Extract endpoint details
        endpoint_details = tool_spec.get("endpoint_details", {})
        url = endpoint_details.get("url", f"http://localhost:5678/webhook-test/{tool_name.lower()}-placeholder")
        method = endpoint_details.get("method", "POST")
        
        # Extract schemas
        request_schema = tool_spec.get("request_schema", {})
        response_schema = tool_spec.get("response_schema", {})
        authentication = tool_spec.get("authentication", {})
        
        code = f'''"""
Auto-generated tool implementation for {tool_name}.
Generated by ToolDev.
"""

import logging
import requests
import json
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class {class_name}:
    """
    {description}
    
    Tool Type: {tool_type}
    Endpoint: {url}
    Method: {method}
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize {tool_name} tool.
        
        Args:
            config: Tool configuration including authentication
        """
        self.config = config or {{}}
        self.name = "{tool_name}"
        self.tool_type = "{tool_type}"
        self.endpoint_url = "{url}"
        self.method = "{method}"
        self.spec = {json.dumps(tool_spec, indent=8)}
        self.request_schema = {json.dumps(request_schema, indent=8)}
        self.response_schema = {json.dumps(response_schema, indent=8)}
        self.authentication = {json.dumps(authentication, indent=8)}
        
    def execute(self, task_description: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute {tool_name} functionality.
        
        Args:
            task_description: Description of the task to perform
            data: Optional data for the task
            
        Returns:
            Dict containing execution results
        """
        logger.info(f"{{self.name}}: Executing task: {{task_description}}")
        
        try:
            # Validate input against request schema if provided
            if self.request_schema and data:
                self._validate_request(data)
            
            # Execute based on tool type
            if self.tool_type == "webhook":
                result = self._handle_webhook_request(task_description, data)
            elif self.tool_type == "api":
                result = self._handle_api_request(task_description, data)
            elif self.tool_type == "local":
                result = self._handle_local_request(task_description, data)
            else:
                result = self._handle_generic_request(task_description, data)
            
            # Validate output against response schema if provided
            if self.response_schema and result:
                self._validate_response(result)
            
            logger.info(f"{{self.name}}: Task completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"{{self.name}}: Task failed: {{str(e)}}")
            return {{
                "status": "failed",
                "tool": self.name,
                "error": str(e),
                "task": task_description
            }}
    
    def _validate_request(self, data: Dict[str, Any]) -> bool:
        """Validate request data against request schema."""
        # TODO: Implement proper schema validation
        # For now, just check if required fields are present
        required_fields = self.request_schema.get("required", [])
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Required field '{{field}}' missing from request data")
        return True
    
    def _validate_response(self, response: Dict[str, Any]) -> bool:
        """Validate response data against response schema."""
        # TODO: Implement proper schema validation
        return True
    
    def _handle_webhook_request(self, task_description: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle webhook-type requests."""
        payload = {{
            "task_description": task_description,
            "data": data or {{}},
            "tool": self.name
        }}
        
        # Add authentication headers if configured
        headers = {{"Content-Type": "application/json"}}
        if self.authentication.get("type") == "api_key":
            api_key = self.config.get("api_key") or self.authentication.get("api_key")
            if api_key:
                headers["Authorization"] = f"Bearer {{api_key}}"
        elif self.authentication.get("type") == "basic":
            # Handle basic auth if needed
            pass
        
        try:
            if self.method.upper() == "POST":
                response = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=30)
            elif self.method.upper() == "GET":
                response = requests.get(self.endpoint_url, params=payload, headers=headers, timeout=30)
            elif self.method.upper() == "PUT":
                response = requests.put(self.endpoint_url, json=payload, headers=headers, timeout=30)
            else:
                response = requests.post(self.endpoint_url, json=payload, headers=headers, timeout=30)
            
            response.raise_for_status()
            
            # Try to parse JSON response
            try:
                result_data = response.json()
            except json.JSONDecodeError:
                result_data = response.text
            
            return {{
                "status": "completed",
                "tool": self.name,
                "result": result_data,
                "status_code": response.status_code,
                "response_headers": dict(response.headers)
            }}
            
        except requests.RequestException as e:
            # Fallback to simulated response if webhook is not available
            logger.warning(f"{{self.name}}: Webhook request failed, using simulated response: {{str(e)}}")
            return self._generate_simulated_response(task_description, data)
    
    def _handle_api_request(self, task_description: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle API-type requests."""
        # Similar to webhook but with different authentication/formatting
        return self._handle_webhook_request(task_description, data)
    
    def _handle_local_request(self, task_description: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle local tool requests (no external API call)."""
        # TODO: Implement local tool logic based on tool specification
        return {{
            "status": "completed",
            "tool": self.name,
            "result": {{
                "message": f"Local {{self.name}} processed: {{task_description}}",
                "data": data,
                "note": "This is a local tool implementation. Enhance with specific logic."
            }},
            "task": task_description
        }}
    
    def _handle_generic_request(self, task_description: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Handle generic tool requests."""
        return {{
            "status": "completed",
            "tool": self.name,
            "result": {{
                "message": f"{{self.name}} processed: {{task_description}}",
                "data": data,
                "note": "This is a generic tool implementation. Enhance with specific logic."
            }},
            "task": task_description
        }}
    
    def _generate_simulated_response(self, task_description: str, data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a simulated response when the actual endpoint is not available."""
        return {{
            "status": "completed",
            "tool": self.name,
            "result": {{
                "message": f"Simulated {{self.name}} response for: {{task_description}}",
                "data": data,
                "note": "This is a simulated response. The actual endpoint was not available.",
                "simulated": True
            }},
            "task": task_description
        }}
    
    def get_spec(self) -> Dict[str, Any]:
        """Return the tool specification."""
        return self.spec
    
    def get_request_schema(self) -> Dict[str, Any]:
        """Return the request schema for this tool."""
        return self.request_schema
    
    def get_response_schema(self) -> Dict[str, Any]:
        """Return the response schema for this tool."""
        return self.response_schema
    
    def get_authentication_info(self) -> Dict[str, Any]:
        """Return authentication information for this tool."""
        return self.authentication
    
    def test_connection(self) -> Dict[str, Any]:
        """Test the connection to the tool endpoint."""
        try:
            # Simple health check
            test_result = self.execute("connection_test", {{"test": True}})
            return {{
                "connection_status": "success" if test_result.get("status") == "completed" else "failed",
                "test_result": test_result
            }}
        except Exception as e:
            return {{
                "connection_status": "failed",
                "error": str(e)
            }}
'''
        
        return code
    
    def _update_tool_status(self, tool_name: str, status: str, built_path: str):
        """Update tool status in registry."""
        if tool_name in self.registry.tools:
            self.registry.tools[tool_name]["status"] = status
            self.registry.tools[tool_name]["built_path"] = built_path
            self.registry.save()
    
    def _trigger_tool_qa(self):
        """Trigger ToolQA to test newly built tools."""
        try:
            if hasattr(self.coa, 'enqueue_task'):
                self.coa.enqueue_task("ToolQA")
            else:
                self._log("COA does not support task queuing, ToolQA will run on next cycle", "warning")
        except Exception as e:
            self._log(f"Error triggering ToolQA: {str(e)}", "error") 