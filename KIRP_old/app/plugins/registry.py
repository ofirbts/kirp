"""
KIRP Plugin Registry v7
Production plugin management
"""
from typing import Dict, Callable, List
from abc import ABC, abstractmethod

class Plugin(ABC):
    """Plugin interface"""
    @abstractmethod
    async def execute(self, context: Dict) -> Dict:
        pass

class PluginRegistry:
    """Production plugin system"""
    def __init__(self):
        self.plugins: Dict[str, Plugin] = {}
    
    def register(self, name: str, plugin: Plugin):
        self.plugins[name] = plugin
    
    async def execute_pipeline(self, pipeline: List[str], context: Dict) -> Dict:
        """Execute plugin pipeline"""
        result = context.copy()
        for plugin_name in pipeline:
            if plugin_name in self.plugins:
                result = await self.plugins[plugin_name].execute(result)
        return result

registry = PluginRegistry()
