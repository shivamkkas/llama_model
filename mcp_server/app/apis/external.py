"""
API Manager for calling external APIs with caching
"""
from typing import Dict, List, Optional, Any
import json
import hashlib
from datetime import datetime, timedelta
import aiohttp
import asyncio
from pathlib import Path

from config.config import Config


class APIRegistry:
    """Registry for external APIs"""
    
    def __init__(self, registry_path: str):
        self.registry_path = registry_path
        self.apis: Dict[str, Dict[str, Any]] = {}
        self._load_registry()
    
    def _load_registry(self):
        """Load API registry from file"""
        if Path(self.registry_path).exists():
            with open(self.registry_path, 'r') as f:
                self.apis = json.load(f)
    
    def _save_registry(self):
        """Save API registry to file"""
        Path(self.registry_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.registry_path, 'w') as f:
            json.dump(self.apis, f, indent=2)
    
    def register_api(
        self,
        name: str,
        base_url: str,
        description: str,
        endpoints: List[Dict[str, Any]],
        auth_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register a new external API"""
        
        api_id = hashlib.md5(name.encode()).hexdigest()[:8]
        
        self.apis[api_id] = {
            "id": api_id,
            "name": name,
            "base_url": base_url,
            "description": description,
            "endpoints": endpoints,
            "auth_config": auth_config or {},
            "registered_at": datetime.now().isoformat()
        }
        
        self._save_registry()
        return api_id
    
    def get_api(self, api_name: str) -> Optional[Dict[str, Any]]:
        """Get API configuration by name"""
        for api in self.apis.values():
            if api['name'].lower() == api_name.lower():
                return api
        return None
    
    def list_apis(self) -> List[Dict[str, Any]]:
        """List all registered APIs"""
        return [
            {
                "id": api["id"],
                "name": api["name"],
                "description": api["description"],
                "base_url": api["base_url"],
                "endpoints": [ep["path"] for ep in api["endpoints"]]
            }
            for api in self.apis.values()
        ]
    
    def delete_api(self, api_id: str):
        """Delete an API from registry"""
        if api_id in self.apis:
            del self.apis[api_id]
            self._save_registry()


class APICache:
    """Simple in-memory cache for API responses"""
    
    def __init__(self, ttl: int = 3600):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = ttl
    
    def _get_cache_key(self, api_name: str, endpoint: str, params: Dict) -> str:
        """Generate cache key"""
        key_data = f"{api_name}:{endpoint}:{json.dumps(params, sort_keys=True)}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, api_name: str, endpoint: str, params: Dict) -> Optional[Any]:
        """Get cached response"""
        key = self._get_cache_key(api_name, endpoint, params)
        
        if key in self.cache:
            cached = self.cache[key]
            if datetime.now() < cached['expires_at']:
                return cached['data']
            else:
                del self.cache[key]
        
        return None
    
    def set(self, api_name: str, endpoint: str, params: Dict, data: Any):
        """Cache a response"""
        key = self._get_cache_key(api_name, endpoint, params)
        self.cache[key] = {
            'data': data,
            'expires_at': datetime.now() + timedelta(seconds=self.ttl),
            'cached_at': datetime.now().isoformat()
        }
    
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()


class APIManager:
    def __init__(self, config: Config):
        self.config = config
        self.registry = APIRegistry(config.apis.registry_path)
        self.cache = APICache(ttl=config.apis.cache_ttl)
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def initialize(self):
        """Initialize HTTP session"""
        timeout = aiohttp.ClientTimeout(total=self.config.apis.timeout)
        self.session = aiohttp.ClientSession(timeout=timeout)
        print("✓ Initialized API manager")
    
    async def register_api(
        self,
        name: str,
        base_url: str,
        description: str,
        endpoints: List[Dict[str, Any]],
        auth_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Register an external API"""
        return self.registry.register_api(
            name=name,
            base_url=base_url,
            description=description,
            endpoints=endpoints,
            auth_config=auth_config
        )
    
    async def call_api(
        self,
        api_name: str,
        params: Dict[str, Any],
        endpoint: Optional[str] = None,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Call an external API"""
        
        # Get API configuration
        api_config = self.registry.get_api(api_name)
        if not api_config:
            raise ValueError(f"API '{api_name}' not found in registry")
        
        # Determine endpoint
        if not endpoint and api_config['endpoints']:
            endpoint = api_config['endpoints'][0]['path']
        
        if not endpoint:
            raise ValueError("No endpoint specified")
        
        # Check cache
        if use_cache:
            cached_result = self.cache.get(api_name, endpoint, params)
            if cached_result is not None:
                return {
                    "status": "success",
                    "data": cached_result,
                    "cached": True
                }
        
        # Build URL
        url = f"{api_config['base_url'].rstrip('/')}/{endpoint.lstrip('/')}"
        
        # Prepare headers
        headers = {}
        auth_config = api_config.get('auth_config', {})
        
        if auth_config.get('type') == 'bearer':
            headers['Authorization'] = f"Bearer {auth_config['token']}"
        elif auth_config.get('type') == 'api_key':
            headers[auth_config['header_name']] = auth_config['api_key']
        
        # Make request with retries
        for attempt in range(self.config.apis.max_retries):
            try:
                # Determine HTTP method from endpoint config
                endpoint_config = next(
                    (ep for ep in api_config['endpoints'] if ep['path'] == endpoint),
                    None
                )
                method = endpoint_config.get('method', 'GET') if endpoint_config else 'GET'
                
                if method.upper() == 'GET':
                    async with self.session.get(url, params=params, headers=headers) as response:
                        response.raise_for_status()
                        data = await response.json()
                
                elif method.upper() == 'POST':
                    async with self.session.post(url, json=params, headers=headers) as response:
                        response.raise_for_status()
                        data = await response.json()
                
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Cache successful response
                if use_cache:
                    self.cache.set(api_name, endpoint, params, data)
                
                return {
                    "status": "success",
                    "data": data,
                    "cached": False
                }
            
            except aiohttp.ClientError as e:
                if attempt == self.config.apis.max_retries - 1:
                    return {
                        "status": "error",
                        "error": str(e),
                        "attempts": attempt + 1
                    }
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    async def list_apis(self) -> List[Dict[str, Any]]:
        """List all registered APIs"""
        return self.registry.list_apis()
    
    async def delete_api(self, api_id: str):
        """Delete an API from registry"""
        self.registry.delete_api(api_id)
    
    async def clear_cache(self):
        """Clear API cache"""
        self.cache.clear()
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.session:
            await self.session.close()
            print("✓ API manager cleanup complete")