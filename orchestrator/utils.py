import os
import logging
import re

logger = logging.getLogger(__name__)

class TemplateError(Exception):
    """Raised when a template cannot be loaded."""
    pass

def load_template(name: str) -> str:
    """Load a template file with error handling."""
    try:
        # Try relative path first (when running from orchestrator directory)
        path = os.path.join("templates", f"{name}.txt")
        if not os.path.exists(path):
            # Fallback to absolute path (when running from parent directory)
            path = os.path.join("orchestrator", "templates", f"{name}.txt")
        
        with open(path) as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"Template file not found: {path}")
        raise TemplateError(f"Template '{name}' not found")
    except Exception as e:
        logger.error(f"Error loading template {name}: {str(e)}")
        raise TemplateError(f"Error loading template '{name}': {str(e)}")

def _extract_json_from_string(text: str) -> str | None:
    """Extracts the first valid JSON object from a string, looking for ```json ... ``` or raw object."""
    # First try to find JSON in code blocks: ```json ... ```
    json_block_match = re.search(r'```json\s*(\{[\s\S]*?\}|\[[\s\S]*?\])\s*```', text, re.DOTALL)
    if json_block_match:
        return json_block_match.group(1)
    
    # Then try to find raw JSON objects or arrays
    raw_json_match = re.search(r'(\{[\s\S]*?\}|\[[\s\S]*?\])', text, re.DOTALL)
    if raw_json_match:
        return raw_json_match.group(1)
    
    return None 