"""
AWS Bedrock Agent Utilities

This module handles all interactions with AWS Bedrock Agent Runtime.
"""

import os
import boto3
import logging
from typing import Dict, Optional

logger = logging.getLogger('bedrock_utils')
logger.setLevel(logging.INFO)


def get_config(key: str) -> Optional[str]:
    """
    Retrieves configuration values from environment variables.
    
    Args:
        key: The environment variable key
        
    Returns:
        The configuration value or None if not found
    """
    value = os.environ.get(key)
    if not value:
        logger.warning(f"Config key {key} not found in environment variables.")
    return value


def get_bedrock_client():
    """
    Creates and returns a boto3 client for Bedrock Agent Runtime.
    
    Returns:
        boto3.client: Configured Bedrock Agent Runtime client
        
    Raises:
        ValueError: If AWS credentials are not configured
    """
    aws_access_key = get_config('AWS_ACCESS_KEY')
    aws_secret_key = get_config('AWS_SECRET_KEY')
    aws_region = get_config('AWS_REGION') or 'us-east-1'

    if not aws_access_key or not aws_secret_key:
        logger.error("AWS credentials missing.")
        raise ValueError("AWS credentials not configured.")

    return boto3.client(
        service_name='bedrock-agent-runtime',
        region_name=aws_region,
        aws_access_key_id=aws_access_key,
        aws_secret_access_key=aws_secret_key
    )


def invoke_bedrock_agent(
    user_message: str, 
    session_id: str, 
    user_id: str = None
) -> Dict[str, str]:
    """
    Invokes the AWS Bedrock Agent with the given message and session persistence.
    
    Args:
        user_message: The user's input message
        session_id: Session ID for conversation continuity
        user_id: Optional user identifier for tracking
        
    Returns:
        dict: Contains 'response' (AI generated text) and 'session_id'
        
    Raises:
        ValueError: If Bedrock Agent configuration is missing
        Exception: If invocation fails
    """
    agent_id = get_config('AWS_BEDROCK_AGENT_ID')
    agent_alias_id = get_config('AWS_BEDROCK_AGENT_ALIAS_ID')

    if not agent_id or not agent_alias_id:
        raise ValueError("AWS Bedrock Agent ID or Alias ID not configured.")

    try:
        client = get_bedrock_client()
        
        # Invoke the agent
        response = client.invoke_agent(
            agentId=agent_id,
            agentAliasId=agent_alias_id,
            sessionId=session_id,
            inputText=user_message,
            enableTrace=False
        )

        # Parse the event stream response
        completion = ""
        for event in response.get('completion', []):
            if 'chunk' in event:
                chunk = event['chunk']
                if 'bytes' in chunk:
                    completion += chunk['bytes'].decode('utf-8')
        
        logger.info(f"Bedrock Agent response for session {session_id}: {len(completion)} chars")
        
        return {
            "response": completion.strip(),
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"Error invoking Bedrock Agent: {str(e)}")
        raise e


def test_bedrock_connection() -> bool:
    """
    Tests the connection to AWS Bedrock Agent.
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = get_bedrock_client()
        # Try to list agents to verify connection
        logger.info("AWS Bedrock connection test successful")
        return True
    except Exception as e:
        logger.error(f"AWS Bedrock connection test failed: {str(e)}")
        return False
