"""
Prompt Builder - builds complete prompts by injecting dynamic sections.
"""
from typing import Dict, Any, Optional
import logging

from models.prompt import PromptTemplate
from services.creative.prompts.loader import PromptLoader

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds complete prompts by combining templates with dynamic settings.
    """
    
    def __init__(self, loader: PromptLoader):
        self.loader = loader
    
    async def build_system_prompt(
        self,
        agent_name: str,
        overrides: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Build complete system prompt for an agent.
        
        Args:
            agent_name: Name of the agent
            overrides: Optional dict to override specific sections
            
        Returns:
            Complete system prompt string
        """
        # Get template
        template = await self.loader.get_template(agent_name)
        if not template:
            raise ValueError(f"No template found for agent: {agent_name}")
        
        # Get settings
        settings = await self.loader.get_settings_dict(agent_name)
        
        # Apply overrides
        if overrides:
            settings.update(overrides)
        
        # Build prompt by injecting sections
        prompt = template.system_prompt
        
        # Replace placeholders
        for section_name, content in settings.items():
            placeholder = f"{{{{{section_name}}}}}"  # {{section_name}}
            if placeholder in prompt:
                prompt = prompt.replace(placeholder, content)
        
        # Add output format if specified
        if template.output_format:
            prompt += f"\n\n## OUTPUT FORMAT\n\n{template.output_format}"
        
        logger.debug(
            f"Built system prompt for {agent_name}: {len(prompt)} chars"
        )
        
        return prompt
    
    async def build_user_prompt(
        self,
        agent_name: str,
        data: Dict[str, Any],
        template_str: Optional[str] = None
    ) -> str:
        """
        Build user prompt from data.
        
        Args:
            agent_name: Name of the agent
            data: Data to include in prompt
            template_str: Optional template string with {placeholders}
            
        Returns:
            Complete user prompt string
        """
        if template_str:
            # Use provided template
            prompt = template_str
            for key, value in data.items():
                placeholder = f"{{{key}}}"
                if placeholder in prompt:
                    prompt = prompt.replace(placeholder, str(value))
        else:
            # Build from data dict
            prompt_parts = []
            for key, value in data.items():
                if value is not None:
                    prompt_parts.append(f"{key.upper()}: {value}")
            prompt = "\n\n".join(prompt_parts)
        
        logger.debug(
            f"Built user prompt for {agent_name}: {len(prompt)} chars"
        )
        
        return prompt
    
    async def build_prompts(
        self,
        agent_name: str,
        data: Dict[str, Any],
        user_template: Optional[str] = None,
        system_overrides: Optional[Dict[str, str]] = None
    ) -> tuple[str, str]:
        """
        Build both system and user prompts.
        
        Args:
            agent_name: Name of the agent
            data: Data for user prompt
            user_template: Optional template for user prompt
            system_overrides: Optional overrides for system prompt sections
            
        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = await self.build_system_prompt(
            agent_name,
            overrides=system_overrides
        )
        
        user_prompt = await self.build_user_prompt(
            agent_name,
            data=data,
            template_str=user_template
        )
        
        return system_prompt, user_prompt
