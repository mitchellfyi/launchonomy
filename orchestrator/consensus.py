#!/usr/bin/env python3
"""
Consensus voting system for Launchonomy.
Enforces 100% unanimous approval for all proposals to ensure nothing slips through.
"""

import logging
from typing import Dict, Any, List

try:
    from orchestrator.registry import Registry
except ImportError:
    # Fallback for when running from within orchestrator directory
    from registry import Registry

logger = logging.getLogger(__name__)

def propose_and_vote(proposal: Dict[str, Any]) -> bool:
    """
    Implements strict consensus voting with 100% approval requirement.
    
    Args:
        proposal: Dictionary containing proposal details with keys:
                 - type: "add_tool" or "add_agent"
                 - name: Name of the item to add
                 - spec: Specification dictionary
                 - endpoint: (for agents) Endpoint information
    
    Returns:
        bool: True if ALL agents vote "yes", False otherwise
    """
    proposal_type = proposal.get("type", "unknown")
    proposal_name = proposal.get("name", "unnamed")
    
    logger.info(f"Starting consensus vote for {proposal_type} '{proposal_name}'")
    
    # Load registry to get active agents
    try:
        registry = Registry()
        agent_names = registry.list_agent_names()
        
        if not agent_names:
            logger.warning("No agents found in registry for voting")
            return False
            
        logger.debug(f"Found {len(agent_names)} agents for voting: {agent_names}")
        
    except Exception as e:
        logger.error(f"Failed to load registry for voting: {e}")
        return False
    
    votes = []
    vote_details = []
    
    for agent_name in agent_names:
        try:
            # Get agent specification from registry
            agent_spec = registry.get_agent_spec(agent_name)
            if not agent_spec:
                logger.warning(f"Agent '{agent_name}' not found in registry, treating as 'no' vote")
                votes.append(False)
                vote_details.append((agent_name, "no", "agent_not_found"))
                continue
            
            # For now, we'll implement a simple voting logic since we don't have
            # actual agent instances with vote_on methods in the registry
            # This is a placeholder that can be enhanced when agent instances are available
            
            # Simple voting logic based on agent type and proposal
            vote = _get_agent_vote(agent_name, agent_spec, proposal)
            
            votes.append(vote.lower() == "yes")
            vote_details.append((agent_name, vote, "voted"))
            logger.debug(f"Agent '{agent_name}' voted: {vote}")
            
        except Exception as e:
            logger.warning(f"Error getting vote from agent '{agent_name}': {e}, treating as 'no'")
            votes.append(False)
            vote_details.append((agent_name, "no", f"error: {str(e)}"))
    
    # Calculate results
    yes_votes = sum(votes)
    total_votes = len(votes)
    unanimous = all(votes)
    
    # Log detailed results
    logger.info(f"Vote results for {proposal_type} '{proposal_name}': {yes_votes}/{total_votes} yes votes")
    for agent_name, vote, reason in vote_details:
        logger.debug(f"  {agent_name}: {vote} ({reason})")
    
    if unanimous and total_votes > 0:
        logger.info(f"Proposal {proposal_type} '{proposal_name}' ACCEPTED by unanimous consent")
        return True
    else:
        logger.info(f"Proposal {proposal_type} '{proposal_name}' REJECTED (requires 100% approval)")
        return False

def _get_agent_vote(agent_name: str, agent_spec: Dict[str, Any], proposal: Dict[str, Any]) -> str:
    """
    Determines how an agent would vote on a proposal based on its specification.
    This is a placeholder implementation until we have actual agent instances with vote_on methods.
    
    Args:
        agent_name: Name of the agent
        agent_spec: Agent specification from registry
        proposal: The proposal being voted on
    
    Returns:
        str: "yes" or "no"
    """
    proposal_type = proposal.get("type")
    proposal_spec = proposal.get("spec", {})
    
    # OrchestrationAgent and AutoProvisionAgent should approve auto-provisioned items
    if agent_name in ["OrchestrationAgent", "AutoProvisionAgent"]:
        if proposal_type in ["add_tool", "add_agent"]:
            # Approve auto-provisioned items and well-formed proposals
            if proposal_spec.get("source") == "auto-provisioned":
                return "yes"
            # Also approve if proposal has required fields
            if proposal.get("name") and proposal_spec:
                return "yes"
    
    # For other agents, be more conservative
    # In a real implementation, this would call agent.vote_on(proposal)
    if proposal_type in ["add_tool", "add_agent"] and proposal_spec.get("source") == "auto-provisioned":
        # Auto-provisioned items that passed triviality check should generally be approved
        return "yes"
    
    # Default to "no" for safety (100% consensus requirement)
    return "no"

def get_voting_agents() -> List[str]:
    """
    Returns a list of agent names that can participate in voting.
    
    Returns:
        List[str]: List of agent names from the registry
    """
    try:
        registry = Registry()
        return registry.list_agent_names()
    except Exception as e:
        logger.error(f"Failed to get voting agents: {e}")
        return []

if __name__ == "__main__":
    # Test the consensus system manually
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    
    print("🗳️  Testing Consensus Voting System")
    print("=" * 50)
    
    # Test 1: Auto-provisioned tool proposal
    dummy_tool_proposal = {
        "type": "add_tool",
        "name": "test_spreadsheet_tool",
        "spec": {
            "description": "Auto-provisioned stub for tool: test_spreadsheet_tool",
            "type": "webhook",
            "endpoint_details": {
                "url": "http://localhost:5678/webhook-test/test_spreadsheet_tool-placeholder",
                "method": "POST"
            },
            "source": "auto-provisioned"
        }
    }
    
    print("\n📋 Test 1: Auto-provisioned tool proposal")
    result1 = propose_and_vote(dummy_tool_proposal)
    print(f"Result: {'✅ ACCEPTED' if result1 else '❌ REJECTED'}")
    
    # Test 2: Manual agent proposal (should be more restrictive)
    dummy_agent_proposal = {
        "type": "add_agent",
        "name": "test_manual_agent",
        "spec": {
            "description": "Manually proposed agent",
            "capabilities": ["testing"]
        },
        "endpoint": "test_agents.test_manual_agent.handle"
    }
    
    print("\n🤖 Test 2: Manual agent proposal")
    result2 = propose_and_vote(dummy_agent_proposal)
    print(f"Result: {'✅ ACCEPTED' if result2 else '❌ REJECTED'}")
    
    # Test 3: Invalid proposal
    invalid_proposal = {
        "type": "invalid_type",
        "name": "test_invalid"
    }
    
    print("\n❌ Test 3: Invalid proposal")
    result3 = propose_and_vote(invalid_proposal)
    print(f"Result: {'✅ ACCEPTED' if result3 else '❌ REJECTED'}")
    
    # Show voting agents
    agents = get_voting_agents()
    print(f"\n👥 Available voting agents: {agents}")
    
    print("\n🎉 Consensus testing complete!") 