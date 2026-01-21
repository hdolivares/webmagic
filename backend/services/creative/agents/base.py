"""
Base Agent class for all AI agents.
Handles Claude API communication, error handling, and retry logic.
"""
from typing import Dict, Any, Optional, List
from anthropic import Anthropic, AsyncAnthropic
from anthropic.types import Message
import json
import logging
from core.config import get_settings
from core.exceptions import ExternalAPIException

logger = logging.getLogger(__name__)
settings = get_settings()


class BaseAgent:
    """
    Base class for all AI agents.
    Provides Claude API wrapper with error handling and JSON parsing.
    """
    
    def __init__(
        self,
        agent_name: str,
        model: str = "claude-3-5-sonnet-20240620",
        temperature: float = 0.7,
        max_tokens: int = 4096
    ):
        """
        Initialize base agent.
        
        Args:
            agent_name: Name of the agent (for logging)
            model: Claude model to use
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
        """
        self.agent_name = agent_name
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        logger.info(
            f"Initialized {agent_name} agent with model {model}"
        )
    
    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> str:
        """
        Generate text completion from Claude.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            Generated text
            
        Raises:
            ExternalAPIException: If API call fails
        """
        try:
            logger.info(f"[{self.agent_name}] Generating completion...")
            logger.debug(f"System prompt length: {len(system_prompt)} chars")
            logger.debug(f"User prompt length: {len(user_prompt)} chars")
            
            message = await self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens or self.max_tokens,
                temperature=temperature or self.temperature,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )
            
            # Extract text content
            content = message.content[0].text
            
            logger.info(
                f"[{self.agent_name}] Generation complete. "
                f"Output length: {len(content)} chars"
            )
            
            return content
            
        except Exception as e:
            logger.error(
                f"[{self.agent_name}] API error: {str(e)}",
                exc_info=True
            )
            raise ExternalAPIException(
                f"Claude API failed for {self.agent_name}: {str(e)}"
            )
    
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate JSON completion from Claude.
        Automatically parses and validates JSON.
        
        Args:
            system_prompt: System instructions (should specify JSON output)
            user_prompt: User message
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            
        Returns:
            Parsed JSON dictionary
            
        Raises:
            ExternalAPIException: If API call fails
            ValueError: If response is not valid JSON
        """
        # Add JSON instruction to system prompt if not present
        if "json" not in system_prompt.lower():
            system_prompt += "\n\nYou must respond with valid JSON only. No markdown, no explanation."
        
        # Generate text
        text = await self.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Parse JSON
        try:
            # Clean markdown code blocks if present
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            logger.info(f"[{self.agent_name}] Successfully parsed JSON")
            return data
            
        except json.JSONDecodeError as e:
            logger.error(
                f"[{self.agent_name}] Failed to parse JSON: {str(e)}\n"
                f"Raw output: {text[:500]}..."
            )
            raise ValueError(
                f"Invalid JSON response from {self.agent_name}: {str(e)}"
            )
    
    async def generate_with_retry(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3,
        as_json: bool = False
    ) -> Any:
        """
        Generate with automatic retry on failure.
        
        Args:
            system_prompt: System instructions
            user_prompt: User message
            max_retries: Maximum retry attempts
            as_json: If True, parse as JSON
            
        Returns:
            Generated text or parsed JSON
            
        Raises:
            ExternalAPIException: If all retries fail
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                if as_json:
                    return await self.generate_json(system_prompt, user_prompt)
                else:
                    return await self.generate(system_prompt, user_prompt)
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    f"[{self.agent_name}] Attempt {attempt + 1}/{max_retries} failed: {str(e)}"
                )
                
                if attempt < max_retries - 1:
                    # Add clarification to prompt for next retry
                    if as_json and isinstance(e, ValueError):
                        user_prompt += "\n\nPLEASE RESPOND WITH VALID JSON ONLY. No markdown code blocks, no explanations."
        
        # All retries failed
        raise ExternalAPIException(
            f"All {max_retries} attempts failed for {self.agent_name}: {str(last_error)}"
        )
    
    def _log_generation(
        self,
        input_data: Dict[str, Any],
        output_data: Any,
        duration_ms: float
    ):
        """
        Log generation details for debugging.
        
        Args:
            input_data: Input provided to agent
            output_data: Output from agent
            duration_ms: Time taken in milliseconds
        """
        logger.info(
            f"[{self.agent_name}] Generation completed in {duration_ms:.2f}ms"
        )
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Input: {json.dumps(input_data, indent=2)[:500]}...")
            logger.debug(f"Output: {json.dumps(output_data, indent=2)[:500]}...")
