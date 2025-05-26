import logging
from typing import Dict, Any, Optional, List

# Assuming Registry is in orchestrator.registry
# from orchestrator.registry import Registry 
# Assuming OrchestratorAgent will be passed and has agent creation capabilities
# from orchestrator.orchestrator_agent import OrchestratorAgent 

logger = logging.getLogger(__name__)

class AutoProvisionAgent:
    """
    Watches for any user prompt or missing-tool error that meets
    "trivial" criteria, then auto-proposes the minimal agent or tool
    to handle it, submits it to consensus, and—if accepted—installs it.
    """
    def __init__(self, registry, orchestrator, mission_context: Optional[Dict[str, Any]] = None): # Type hints will be added once orchestrator structure is clear
        """
        Initializes the AutoProvisionAgent.
        :param registry: An instance of the Registry class.
        :param orchestrator: The orchestrator agent that manages the mission
        :param mission_context: Mission context information
        """
        self.registry = registry
        self.orchestrator = orchestrator
        self.mission_context = mission_context or {}
        self.name = "AutoProvisionAgent" # For logging and identification

    def _log(self, message: str, level: str = "info"):
        # Helper for logging, assuming orchestrator might have a more complex logger setup
        log_func = getattr(logger, level, logger.info)
        log_func(f"{self.name}: {message}")
        if hasattr(self.orchestrator, '_log_to_monitor') and callable(self.orchestrator._log_to_monitor):
             # If orchestrator has a way to log to the main UI monitor
            self.orchestrator._log_to_monitor(message, level)


    def is_trivial(self, context: Dict, missing_item_details: Dict) -> bool:
        """
        Determines if a missing item request is "trivial" enough for auto-provisioning.
        
        :param context: Current operational context (e.g., overall mission, current step).
        :param missing_item_details: Dict with info like {"type": "tool"/"agent", "name": "ItemName", "reason": "not_found"/"user_request", "details": "..."}
        :return: True if trivial, False otherwise.
        """
        # Placeholder: For now, let's consider any missing tool triggered by a "not_found" reason as potentially trivial.
        # A more sophisticated check would involve LLM evaluation of 'details' or specific keywords.
        item_type = missing_item_details.get("type")
        item_name = missing_item_details.get("name")
        reason = missing_item_details.get("reason")

        self._log(f"Assessing triviality for {item_type} '{item_name}'. Reason: {reason}", "debug")

        if item_type == "tool" and reason == "not_found":
            # Enhanced triviality detection for common business tools
            trivial_tool_patterns = [
                # Core business tools
                "spreadsheet", "calendar", "email", "file", "document", "storage",
                "crm", "analytics", "payment", "webhook", "api", "database",
                "social", "marketing", "automation", "integration", "notification",
                
                # Market research and scanning tools
                "market", "research", "competitor", "analysis", "trend", "keyword",
                "monitoring", "scan", "opportunity", "demand",
                
                # Deployment and hosting tools
                "hosting", "domain", "registration", "deploy", "server", "cloud",
                "infrastructure", "cdn", "ssl", "certificate",
                
                # Development tools
                "code", "generation", "template", "library", "framework", "build",
                "test", "debug", "version", "git",
                
                # Campaign and growth tools
                "campaign", "advertising", "ads", "content", "seo", "conversion",
                "funnel", "growth", "viral", "referral", "retention",
                
                # Analytics and tracking tools
                "tracking", "metrics", "dashboard", "reporting", "insights",
                "performance", "optimization", "ab_test", "cohort"
            ]
            
            if any(pattern in item_name.lower() for pattern in trivial_tool_patterns):
                self._log(f"'{item_name}' considered TRIVIAL for auto-provisioning.", "info")
                return True
        
        # Add criteria for trivial agent requests if necessary
        # if item_type == "agent" and reason == "user_request":
        #     # e.g. if user asks for a very simple task like "summarize this text"
        #     pass

        self._log(f"'{item_name}' NOT considered trivial.", "info")
        return False

    async def generate_real_tool_spec(self, item_name: str, item_type: str, context: Optional[Dict] = None) -> Dict:
        """
        Generates a real tool specification using AI assistance to create functional tools.
        
        :param item_name: Name of the tool/agent.
        :param item_type: "tool" or "agent".
        :param context: Optional context that might influence the tool creation.
        :return: A dictionary representing the item's specification.
        """
        self._log(f"Generating real tool spec for {item_type} '{item_name}'.", "info")
        
        if item_type == "tool":
            try:
                # Use OpenAI to generate real tool implementation
                import openai
                import os
                
                openai_api_key = os.getenv("OPENAI_API_KEY")
                if not openai_api_key:
                    self._log("No OpenAI API key available for AI-assisted tool creation", "error")
                    return self._generate_fallback_stub(item_name, item_type)
                
                # Create tool generation prompt
                prompt = f"""
You are a tool creation specialist. Create a complete, functional tool specification for "{item_name}".

Context: {context or 'General business automation tool'}

Please provide a JSON specification that includes:
1. A clear description of what the tool does
2. Real API endpoints or service integrations (use actual services like Zapier, IFTTT, or direct APIs)
3. Proper authentication configuration
4. Detailed request and response schemas
5. Error handling specifications
6. Real-world usage examples

For hosting tools: Use services like Vercel, Railway, Netlify, Heroku
For domain tools: Use services like Namecheap, GoDaddy, Cloudflare
For payment tools: Use Stripe, PayPal APIs
For analytics tools: Use Google Analytics, Mixpanel APIs
For email tools: Use SendGrid, Mailchimp APIs

The tool should be immediately usable with real API credentials. Provide actual endpoint URLs and authentication methods.

Return only valid JSON in this format:
{{
    "description": "Detailed description of the tool's functionality",
    "type": "webhook",
    "endpoint_details": {{
        "url": "https://actual-service-url.com/api/endpoint",
        "method": "POST"
    }},
    "authentication": {{
        "type": "api_key|bearer|oauth2",
        "required_credentials": ["api_key", "secret_key"],
        "setup_instructions": "How to get API credentials"
    }},
    "request_schema": {{
        "type": "object",
        "properties": {{ ... }},
        "required": [...]
    }},
    "response_schema": {{
        "type": "object", 
        "properties": {{ ... }}
    }},
    "error_handling": {{
        "common_errors": {{ ... }},
        "retry_logic": "..."
    }},
    "usage_examples": [
        {{
            "description": "Example usage",
            "request": {{ ... }},
            "expected_response": {{ ... }}
        }}
    ],
    "cost_estimate": "Free tier available / $X per month",
    "setup_time": "X minutes",
    "source": "ai-generated-real"
}}
"""

                # Make OpenAI API call
                client = openai.OpenAI(api_key=openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a tool creation expert who provides real, functional tool specifications with actual API integrations."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=2000,
                    temperature=0.3
                )
                
                tool_spec_text = response.choices[0].message.content
                
                # Parse the JSON response
                import json
                try:
                    tool_spec = json.loads(tool_spec_text)
                    tool_spec["source"] = "ai-generated-real"
                    self._log(f"AI-generated real tool spec created for '{item_name}'", "info")
                    return tool_spec
                except json.JSONDecodeError as e:
                    self._log(f"Failed to parse AI-generated tool spec: {e}", "error")
                    return self._generate_fallback_stub(item_name, item_type)
                    
            except Exception as e:
                self._log(f"AI-assisted tool creation failed: {str(e)}", "error")
                return self._generate_fallback_stub(item_name, item_type)
                
        elif item_type == "agent":
            # For agents, create a real agent specification
            return {
                "description": f"AI-generated agent for {item_name}",
                "capabilities": self._determine_agent_capabilities(item_name, context),
                "tools_required": self._determine_required_tools(item_name, context),
                "config": {
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "max_tokens": 1000
                },
                "source": "ai-generated-real"
            }
        else:
            self._log(f"Unknown item type for real spec generation: {item_type}", "error")
            raise ValueError(f"Unknown item type for real spec generation: {item_type}")
    
    def _generate_fallback_stub(self, item_name: str, item_type: str) -> Dict:
        """Generate a basic stub when AI generation fails."""
        self._log(f"Generating fallback stub for {item_type} '{item_name}'.", "warning")
        if item_type == "tool":
            sanitized_name = item_name.lower().replace(" ", "_").replace("-", "_")
            return {
                "description": f"Fallback stub for tool: {item_name} - requires manual configuration",
                "type": "webhook",
                "endpoint_details": {
                    "url": f"http://localhost:5678/webhook-test/{sanitized_name}-placeholder",
                    "method": "POST"
                },
                "authentication": {"type": "none"},
                "request_schema": {
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string"},
                        "data": {"type": "object"}
                    },
                    "required": ["task_description"]
                },
                "response_schema": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "result": {"type": "object"}
                    }
                },
                "source": "fallback-stub",
                "requires_manual_setup": True
            }
        elif item_type == "agent":
            # For agents, a minimal spec
            return {
                "description": f"Auto-provisioned stub for agent: {item_name}",
                "capabilities": ["general_task_execution_stub"], # A generic capability
                "tools_required": [], # Initially no specific tools
                "config": {}, # Placeholder for any future config
                "source": "auto-provisioned"
            }
        else:
            self._log(f"Unknown item type for fallback stub generation: {item_type}", "error")
            raise ValueError(f"Unknown item type for fallback stub generation: {item_type}")
    
    def _determine_agent_capabilities(self, agent_name: str, context: Optional[Dict] = None) -> List[str]:
        """Determine capabilities for an AI-generated agent."""
        name_lower = agent_name.lower()
        capabilities = ["general_task_execution"]
        
        if "research" in name_lower:
            capabilities.extend(["web_search", "data_analysis", "report_generation"])
        elif "marketing" in name_lower:
            capabilities.extend(["campaign_creation", "content_generation", "analytics"])
        elif "sales" in name_lower:
            capabilities.extend(["lead_generation", "crm_integration", "email_automation"])
        elif "support" in name_lower:
            capabilities.extend(["customer_service", "ticket_management", "knowledge_base"])
        elif "dev" in name_lower or "development" in name_lower:
            capabilities.extend(["code_generation", "testing", "deployment"])
        
        return capabilities
    
    def _determine_required_tools(self, agent_name: str, context: Optional[Dict] = None) -> List[str]:
        """Determine required tools for an AI-generated agent."""
        name_lower = agent_name.lower()
        tools = []
        
        if "research" in name_lower:
            tools.extend(["web_search", "data_analysis", "spreadsheet"])
        elif "marketing" in name_lower:
            tools.extend(["social_media", "email_automation", "analytics"])
        elif "sales" in name_lower:
            tools.extend(["crm", "email_automation", "payment_processing"])
        elif "support" in name_lower:
            tools.extend(["ticketing_system", "knowledge_base", "email"])
        elif "dev" in name_lower:
            tools.extend(["code_repository", "hosting", "testing_framework"])
        
        return tools

    async def handle_trivial_request(self, context: Dict, missing_item_details: Dict) -> Optional[str]:
        """
        Handles a potentially trivial request for a missing tool or agent.
        If deemed trivial, proposes it for consensus and applies if accepted.
        
        :param context: Current operational context.
        :param missing_item_details: Details of the missing item.
        :return: A string message if auto-provisioned, None otherwise.
        """
        item_type = missing_item_details.get("type")
        item_name = missing_item_details.get("name")

        self._log(f"Handling request for missing {item_type}: '{item_name}'", "info")

        if not self.is_trivial(context, missing_item_details):
            return None

        # Generate real tool specification using AI
        real_spec = await self.generate_real_tool_spec(item_name, item_type, context)
        
        proposal = {
            "type": f"add_{item_type}", # e.g., "add_tool" or "add_agent"
            "name": item_name,
            "spec": real_spec
        }
        
        if item_type == "agent":
            # Agents also need an endpoint. For stubs, this could be a placeholder
            # or a pointer to a generic handler within a dynamic agent execution framework.
            # For now, registry.apply_proposal has a default if endpoint isn't provided.
            proposal["endpoint"] = f"stub_agents.{item_name.lower()}.handle_request" # Example

        self._log(f"Generated proposal for '{item_name}': {proposal}", "debug")

        # Use the centralized consensus system
        self._log(f"Submitting proposal for {item_type} '{item_name}' to consensus.", "info")
        try:
            # Import consensus system
            try:
                from launchonomy.utils.consensus import propose_and_vote
            except ImportError:
                from consensus import propose_and_vote
            
            vote_result = propose_and_vote(proposal)
        except Exception as e:
            self._log(f"Error during consensus voting for {item_name}: {e}", "error")
            return None # Or handle error more gracefully

        if vote_result:
            self._log(f"Proposal for '{item_name}' ACCEPTED by consensus.", "info")
            try:
                self.registry.apply_proposal(proposal)
                self._log(f"Successfully auto-provisioned {item_type} '{item_name}' and updated registry.", "info")
                
                # For agents, also create the actual RoutedAgent instance
                if item_type == "agent" and hasattr(self.orchestrator, '_create_agent'):
                    try:
                        agent_spec = real_spec
                        persona = agent_spec.get("description", f"Auto-provisioned agent for {item_name}")
                        primer = f"You are {item_name}. {persona}\nYour capabilities include: {', '.join(agent_spec.get('capabilities', []))}"
                        
                        # Create the actual agent instance
                        agent_instance = await self.orchestrator._create_agent(item_name, persona, primer)
                        self._log(f"Created actual agent instance for '{item_name}'.", "info")
                        
                    except Exception as e:
                        self._log(f"Error creating agent instance for {item_name}: {e}", "warning")
                        # Registry entry still exists, but no live agent instance
                
                # Here, one might trigger actual n8n workflow creation if item_type is tool
                # e.g., await self.setup_n8n_webhook_placeholder(item_name, stub_spec)
                return f"Auto-provisioned {item_type} '{item_name}'. You can now use it."
            except Exception as e:
                self._log(f"Error applying accepted proposal for {item_name} to registry: {e}", "error")
                return f"Error applying auto-provisioned {item_type} '{item_name}' to registry after acceptance."
        else:
            self._log(f"Proposal for '{item_name}' REJECTED by consensus.", "warning")
            return None
            
# Example (conceptual) for n8n interaction - to be developed if n8n API is available and configured
# async def setup_n8n_webhook_placeholder(self, tool_name: str, tool_spec: Dict):
#     if tool_spec.get("type") == "webhook" and "n8n.local" in tool_spec.get("endpoint_details", {}).get("url", ""):
#         self._log(f"Attempting to set up n8n webhook placeholder for {tool_name}", "info")
#         # 1. Check if n8n API client is available/configured
#         # 2. Prepare a minimal n8n workflow JSON that listens to the placeholder URL
#         #    and perhaps just returns a static success or logs the input.
#         # 3. Use n8n API to create/import this workflow.
#         # This is a complex step dependent on n8n's API and auth.
#         self._log(f"(Placeholder) n8n webhook for {tool_name} would be set up here.", "info")
#         pass

# To ensure the orchestrator/agents directory is considered a package for imports if needed:
# Create an __init__.py file in orchestrator/agents/
# (This edit_file call will do that, or it can be done manually) 