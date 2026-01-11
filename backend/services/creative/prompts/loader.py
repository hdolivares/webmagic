"""
Prompt Loader - loads prompt templates and settings from database.
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging

from models.prompt import PromptTemplate, PromptSetting

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    Loads prompt templates and settings from database.
    Caches results for performance.
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._template_cache: Dict[str, PromptTemplate] = {}
        self._settings_cache: Dict[str, List[PromptSetting]] = {}
    
    async def get_template(self, agent_name: str) -> Optional[PromptTemplate]:
        """
        Get prompt template for an agent.
        
        Args:
            agent_name: Name of the agent (e.g., "analyst", "concept")
            
        Returns:
            PromptTemplate or None if not found
        """
        # Check cache first
        if agent_name in self._template_cache:
            return self._template_cache[agent_name]
        
        # Load from database
        result = await self.db.execute(
            select(PromptTemplate).where(
                PromptTemplate.agent_name == agent_name
            )
        )
        template = result.scalar_one_or_none()
        
        if template:
            self._template_cache[agent_name] = template
            logger.debug(f"Loaded template for {agent_name}")
        else:
            logger.warning(f"No template found for {agent_name}")
        
        return template
    
    async def get_settings(
        self,
        agent_name: str,
        active_only: bool = True
    ) -> List[PromptSetting]:
        """
        Get all prompt settings for an agent.
        
        Args:
            agent_name: Name of the agent
            active_only: Only return active settings
            
        Returns:
            List of PromptSetting objects
        """
        # Build cache key
        cache_key = f"{agent_name}:{'active' if active_only else 'all'}"
        
        # Check cache
        if cache_key in self._settings_cache:
            return self._settings_cache[cache_key]
        
        # Build query
        query = select(PromptSetting).where(
            PromptSetting.agent_name == agent_name
        )
        
        if active_only:
            query = query.where(PromptSetting.is_active == True)
        
        query = query.order_by(PromptSetting.section_name, PromptSetting.version)
        
        # Load from database
        result = await self.db.execute(query)
        settings = list(result.scalars().all())
        
        # Cache and return
        self._settings_cache[cache_key] = settings
        logger.debug(f"Loaded {len(settings)} settings for {agent_name}")
        
        return settings
    
    async def get_setting(
        self,
        agent_name: str,
        section_name: str
    ) -> Optional[PromptSetting]:
        """
        Get a specific prompt setting by section name.
        Returns the active setting with highest version.
        
        Args:
            agent_name: Name of the agent
            section_name: Name of the section
            
        Returns:
            PromptSetting or None if not found
        """
        result = await self.db.execute(
            select(PromptSetting)
            .where(
                and_(
                    PromptSetting.agent_name == agent_name,
                    PromptSetting.section_name == section_name,
                    PromptSetting.is_active == True
                )
            )
            .order_by(PromptSetting.version.desc())
            .limit(1)
        )
        
        setting = result.scalar_one_or_none()
        
        if not setting:
            logger.warning(
                f"No active setting found for {agent_name}.{section_name}"
            )
        
        return setting
    
    async def get_settings_dict(
        self,
        agent_name: str
    ) -> Dict[str, str]:
        """
        Get all settings as a dictionary {section_name: content}.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Dictionary mapping section names to content
        """
        settings = await self.get_settings(agent_name, active_only=True)
        
        # Build dict, taking highest version for each section
        settings_dict = {}
        for setting in settings:
            if setting.section_name not in settings_dict:
                settings_dict[setting.section_name] = setting.content
        
        return settings_dict
    
    def clear_cache(self):
        """Clear all cached templates and settings."""
        self._template_cache.clear()
        self._settings_cache.clear()
        logger.info("Cleared prompt cache")
    
    async def increment_usage(self, setting_id: str, success: bool = True):
        """
        Increment usage count for a setting.
        
        Args:
            setting_id: UUID of the prompt setting
            success: Whether the generation was successful
        """
        try:
            from uuid import UUID
            from sqlalchemy import update
            
            updates = {"usage_count": PromptSetting.usage_count + 1}
            if success:
                updates["success_count"] = PromptSetting.success_count + 1
            
            await self.db.execute(
                update(PromptSetting)
                .where(PromptSetting.id == UUID(setting_id))
                .values(**updates)
            )
            await self.db.commit()
            
        except Exception as e:
            logger.error(f"Failed to increment usage: {str(e)}")
