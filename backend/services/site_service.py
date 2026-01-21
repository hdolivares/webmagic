"""
Site Management Service

Handles site deployment, URL generation, and file management
for customer websites.

Author: WebMagic Team
Date: January 21, 2026
"""
import os
import shutil
import logging
from pathlib import Path
from typing import Dict, Optional, List
from datetime import datetime

from core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class SiteService:
    """Service for managing customer sites."""
    
    def __init__(self):
        """Initialize site service with configuration."""
        self.base_path = Path(settings.SITES_BASE_PATH)
        self.base_url = settings.SITES_BASE_URL
        self.domain = settings.SITES_DOMAIN
        self.use_path_routing = settings.SITES_USE_PATH_ROUTING
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def generate_site_url(self, slug: str, custom_domain: Optional[str] = None) -> str:
        """
        Generate the public URL for a site.
        
        Args:
            slug: Site slug (e.g., 'la-plumbing-pros')
            custom_domain: Optional custom domain (e.g., 'laplumbingpros.com')
        
        Returns:
            Full URL to the site
        
        Examples:
            >>> service.generate_site_url('la-plumbing-pros')
            'https://sites.lavish.solutions/la-plumbing-pros'
            
            >>> service.generate_site_url('la-plumbing-pros', 'laplumbingpros.com')
            'https://laplumbingpros.com'
        """
        if custom_domain:
            return f"https://{custom_domain}"
        
        if self.use_path_routing:
            return f"{self.base_url}/{slug}"
        else:
            # Subdomain-based (legacy/future option)
            return f"https://{slug}.{self.domain}"
    
    def get_site_path(self, slug: str) -> Path:
        """
        Get the file system path for a site.
        
        Args:
            slug: Site slug
        
        Returns:
            Path object pointing to site directory
        """
        return self.base_path / slug
    
    def validate_slug(self, slug: str) -> bool:
        """
        Validate site slug format.
        
        Rules:
        - Only lowercase letters, numbers, and hyphens
        - Must start and end with alphanumeric
        - Length between 3 and 63 characters
        
        Args:
            slug: Slug to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not slug or len(slug) < 3 or len(slug) > 63:
            return False
        
        # Check format
        if not slug[0].isalnum() or not slug[-1].isalnum():
            return False
        
        # Check characters
        for char in slug:
            if not (char.islower() or char.isdigit() or char == '-'):
                return False
        
        # Prevent double hyphens
        if '--' in slug:
            return False
        
        return True
    
    def site_exists(self, slug: str) -> bool:
        """
        Check if a site directory exists.
        
        Args:
            slug: Site slug
        
        Returns:
            True if site exists, False otherwise
        """
        site_path = self.get_site_path(slug)
        return site_path.exists() and site_path.is_dir()
    
    def deploy_site(
        self,
        slug: str,
        html_content: str,
        css_content: Optional[str] = None,
        js_content: Optional[str] = None,
        assets: Optional[Dict[str, bytes]] = None,
        overwrite: bool = False
    ) -> Dict[str, any]:
        """
        Deploy a site to the file system.
        
        Args:
            slug: Site slug
            html_content: HTML content
            css_content: Optional CSS content
            js_content: Optional JavaScript content
            assets: Optional dictionary of asset files {path: bytes}
            overwrite: Whether to overwrite existing site
        
        Returns:
            Dictionary with deployment info
        
        Raises:
            ValueError: If slug is invalid or site exists and overwrite=False
        """
        # Validate slug
        if not self.validate_slug(slug):
            raise ValueError(f"Invalid slug format: {slug}")
        
        # Check if site exists
        site_path = self.get_site_path(slug)
        if site_path.exists() and not overwrite:
            raise ValueError(f"Site already exists: {slug}")
        
        try:
            # Create/recreate site directory
            if site_path.exists():
                logger.info(f"Removing existing site: {slug}")
                shutil.rmtree(site_path)
            
            site_path.mkdir(parents=True, exist_ok=True)
            
            # Deploy HTML
            html_path = site_path / "index.html"
            html_path.write_text(html_content, encoding='utf-8')
            logger.info(f"Deployed index.html for {slug}")
            
            # Deploy CSS if provided
            if css_content:
                css_dir = site_path / "assets" / "css"
                css_dir.mkdir(parents=True, exist_ok=True)
                css_path = css_dir / "main.css"
                css_path.write_text(css_content, encoding='utf-8')
                logger.info(f"Deployed CSS for {slug}")
            
            # Deploy JavaScript if provided
            if js_content:
                js_dir = site_path / "assets" / "js"
                js_dir.mkdir(parents=True, exist_ok=True)
                js_path = js_dir / "main.js"
                js_path.write_text(js_content, encoding='utf-8')
                logger.info(f"Deployed JavaScript for {slug}")
            
            # Deploy assets if provided
            if assets:
                for asset_path, asset_bytes in assets.items():
                    full_asset_path = site_path / asset_path
                    full_asset_path.parent.mkdir(parents=True, exist_ok=True)
                    full_asset_path.write_bytes(asset_bytes)
                logger.info(f"Deployed {len(assets)} assets for {slug}")
            
            # Set correct permissions
            self._set_permissions(site_path)
            
            # Generate URL
            site_url = self.generate_site_url(slug)
            
            return {
                "success": True,
                "slug": slug,
                "site_url": site_url,
                "site_path": str(site_path),
                "deployed_at": datetime.utcnow().isoformat(),
                "files": {
                    "html": str(html_path),
                    "css": str(css_dir / "main.css") if css_content else None,
                    "js": str(js_dir / "main.js") if js_content else None,
                },
                "asset_count": len(assets) if assets else 0
            }
        
        except Exception as e:
            logger.error(f"Failed to deploy site {slug}: {e}")
            raise
    
    def update_site_file(
        self,
        slug: str,
        file_path: str,
        content: str
    ) -> Dict[str, any]:
        """
        Update a specific file in a site.
        
        Args:
            slug: Site slug
            file_path: Relative path to file (e.g., 'index.html', 'assets/css/main.css')
            content: New content
        
        Returns:
            Dictionary with update info
        """
        if not self.site_exists(slug):
            raise ValueError(f"Site does not exist: {slug}")
        
        site_path = self.get_site_path(slug)
        full_path = site_path / file_path
        
        # Ensure we're not writing outside site directory
        if not full_path.resolve().is_relative_to(site_path.resolve()):
            raise ValueError(f"Invalid file path: {file_path}")
        
        try:
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            full_path.write_text(content, encoding='utf-8')
            
            # Set permissions
            os.chmod(full_path, 0o644)
            
            logger.info(f"Updated file {file_path} for site {slug}")
            
            return {
                "success": True,
                "slug": slug,
                "file_path": file_path,
                "updated_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to update file {file_path} for site {slug}: {e}")
            raise
    
    def delete_site(self, slug: str) -> Dict[str, any]:
        """
        Delete a site and all its files.
        
        Args:
            slug: Site slug
        
        Returns:
            Dictionary with deletion info
        """
        if not self.site_exists(slug):
            raise ValueError(f"Site does not exist: {slug}")
        
        site_path = self.get_site_path(slug)
        
        try:
            shutil.rmtree(site_path)
            logger.info(f"Deleted site: {slug}")
            
            return {
                "success": True,
                "slug": slug,
                "deleted_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to delete site {slug}: {e}")
            raise
    
    def list_sites(self) -> List[Dict[str, any]]:
        """
        List all deployed sites.
        
        Returns:
            List of site information dictionaries
        """
        sites = []
        
        if not self.base_path.exists():
            return sites
        
        for site_dir in self.base_path.iterdir():
            if site_dir.is_dir() and not site_dir.name.startswith('.'):
                slug = site_dir.name
                
                # Get site info
                index_path = site_dir / "index.html"
                if index_path.exists():
                    stat = index_path.stat()
                    
                    sites.append({
                        "slug": slug,
                        "site_url": self.generate_site_url(slug),
                        "site_path": str(site_dir),
                        "last_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                        "size_bytes": stat.st_size
                    })
        
        return sites
    
    def create_version_backup(
        self,
        slug: str,
        version_number: int
    ) -> Dict[str, any]:
        """
        Create a backup of current site version.
        
        Args:
            slug: Site slug
            version_number: Version number for backup
        
        Returns:
            Dictionary with backup info
        """
        if not self.site_exists(slug):
            raise ValueError(f"Site does not exist: {slug}")
        
        site_path = self.get_site_path(slug)
        versions_dir = site_path / "versions"
        versions_dir.mkdir(exist_ok=True)
        
        version_path = versions_dir / f"v{version_number}"
        
        try:
            # Copy current site to version directory
            if version_path.exists():
                shutil.rmtree(version_path)
            
            # Copy all files except versions directory
            shutil.copytree(
                site_path,
                version_path,
                ignore=shutil.ignore_patterns('versions')
            )
            
            logger.info(f"Created version backup v{version_number} for {slug}")
            
            return {
                "success": True,
                "slug": slug,
                "version": version_number,
                "backup_path": str(version_path),
                "created_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to create version backup for {slug}: {e}")
            raise
    
    def restore_version(
        self,
        slug: str,
        version_number: int
    ) -> Dict[str, any]:
        """
        Restore a site to a previous version.
        
        Args:
            slug: Site slug
            version_number: Version number to restore
        
        Returns:
            Dictionary with restore info
        """
        if not self.site_exists(slug):
            raise ValueError(f"Site does not exist: {slug}")
        
        site_path = self.get_site_path(slug)
        version_path = site_path / "versions" / f"v{version_number}"
        
        if not version_path.exists():
            raise ValueError(f"Version v{version_number} does not exist for {slug}")
        
        try:
            # Backup current version before restoring
            current_versions = list((site_path / "versions").glob("v*"))
            next_version = len(current_versions) + 1
            self.create_version_backup(slug, next_version)
            
            # Remove current files (except versions)
            for item in site_path.iterdir():
                if item.name != 'versions':
                    if item.is_dir():
                        shutil.rmtree(item)
                    else:
                        item.unlink()
            
            # Copy version files to site root
            for item in version_path.iterdir():
                if item.is_dir():
                    shutil.copytree(item, site_path / item.name)
                else:
                    shutil.copy2(item, site_path / item.name)
            
            logger.info(f"Restored site {slug} to version v{version_number}")
            
            return {
                "success": True,
                "slug": slug,
                "restored_version": version_number,
                "restored_at": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Failed to restore version v{version_number} for {slug}: {e}")
            raise
    
    def _set_permissions(self, path: Path) -> None:
        """
        Set correct permissions for site files.
        
        Args:
            path: Path to set permissions for
        """
        try:
            # Set directory permissions
            for dirpath, dirnames, filenames in os.walk(path):
                os.chmod(dirpath, 0o755)
                
                # Set file permissions
                for filename in filenames:
                    filepath = Path(dirpath) / filename
                    os.chmod(filepath, 0o644)
            
            logger.debug(f"Set permissions for {path}")
        
        except Exception as e:
            logger.warning(f"Failed to set permissions for {path}: {e}")


# Singleton instance
_site_service = None


def get_site_service() -> SiteService:
    """
    Get singleton instance of SiteService.
    
    Returns:
        SiteService instance
    """
    global _site_service
    if _site_service is None:
        _site_service = SiteService()
    return _site_service
