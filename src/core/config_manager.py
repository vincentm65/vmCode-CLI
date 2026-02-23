

from pathlib import Path
import shutil
from typing import Dict, Any, Optional
import yaml
from llm import config as llm_config


class ConfigManager:

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or llm_config.CONFIG_PATH
        self._cached_data = None

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            return llm_config.generate_config_template()

        try:
            with open(self.config_path, 'r', encoding='utf-8-sig') as f:
                self._cached_data = yaml.safe_load(f) or {}
                return self._cached_data
        except yaml.YAMLError:
            return llm_config.generate_config_template()

    def save(self, config_data: Dict[str, Any], create_backup: bool = False):
        if create_backup and self.config_path.exists():
            backup_path = self.config_path.with_suffix('.backup')
            shutil.copy2(self.config_path, backup_path)

        with open(self.config_path, 'w', encoding='utf-8-sig') as f:
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

        self._cached_data = config_data
        # Note: Config is read from disk on reload. Call reload_config() after changes.

    def update_field(self, key: str, value: Any) -> Optional[Path]:
        config_data = self.load()
        config_data[key] = value

        backup_path = None
        if self.config_path.exists():
            backup_path = self.config_path.with_suffix('.backup')

        self.save(config_data, create_backup=False)
        return backup_path

    def set_provider(self, provider_name: str) -> Optional[Path]:
        return self.update_field('LAST_PROVIDER', provider_name)

    def get_usage_costs(self, provider: str = None, model: str = None) -> Dict[str, float]:
        """Get usage costs for a specific model.

        Args:
            provider: Provider name (e.g., 'openrouter', 'glm', 'openai'). 
                     If None, uses the last provider from config.
            model: Model name (e.g., 'minimax/minimax-m2.5', 'GLM-4.7').
                   If None, uses the current model from the provider.

        Returns:
            Dict with 'in' and 'out' cost values per 1M tokens
        """
        config_data = self.load()
        
        if provider is None:
            provider = config_data.get('LAST_PROVIDER', 'glm')
        
        # Get model name from config if not provided
        if model is None:
            provider_model_map = {
                'openrouter': 'OPENROUTER_MODEL',
                'glm': 'GLM_MODEL',
                'openai': 'OPENAI_MODEL',
                'gemini': 'GEMINI_MODEL',
                'minimax': 'MINIMAX_MODEL',
                'anthropic': 'ANTHROPIC_MODEL',
                'kimi': 'KIMI_MODEL'
            }
            model_key = provider_model_map.get(provider.lower())
            if model_key:
                model = config_data.get(model_key, '')
        
        # Check for model-specific pricing
        model_prices = config_data.get('MODEL_PRICES', {})
        if model and model in model_prices:
            model_cost = model_prices[model]
            return {
                'in': float(model_cost.get('cost_in', 0.0)),
                'out': float(model_cost.get('cost_out', 0.0))
            }
        
        return {'in': 0.0, 'out': 0.0}

    def set_model(self, provider_name: str, model: str) -> Optional[Path]:
        """Set model for a specific provider.

        Args:
            provider_name: Provider name (e.g., 'openrouter', 'glm', 'local', 'openai')
            model: Model name/path to set

        Returns:
            Backup path if backup was created, None otherwise
        """
        # Map provider names to their config keys
        provider_keys = {
            'local': 'LOCAL_MODEL_PATH',
            'openrouter': 'OPENROUTER_MODEL',
            'glm': 'GLM_MODEL',
            'openai': 'OPENAI_MODEL',
            'gemini': 'GEMINI_MODEL',
            'minimax': 'MINIMAX_MODEL',
            'anthropic': 'ANTHROPIC_MODEL',
            'kimi': 'KIMI_MODEL'
        }

        if provider_name not in provider_keys:
            raise ValueError(f"Unknown provider: {provider_name}")

        key = provider_keys[provider_name]
        return self.update_field(key, model)

    def set_api_key(self, provider_name: str, api_key: str) -> Optional[Path]:
        """Set API key for a specific provider.

        Args:
            provider_name: Provider name (e.g., 'openrouter', 'glm', 'openai')
            api_key: API key to set

        Returns:
            Backup path if backup was created, None otherwise
        """
        # Map provider names to their config keys
        provider_keys = {
            'openrouter': 'OPENROUTER_API_KEY',
            'glm': 'GLM_API_KEY',
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'minimax': 'MINIMAX_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'kimi': 'KIMI_API_KEY'
        }

        if provider_name not in provider_keys:
            raise ValueError(f"Unknown provider: {provider_name}")

        key = provider_keys[provider_name]
        return self.update_field(key, api_key)

    def get_pre_tool_planning(self) -> bool:
        """Get the pre-tool planning enabled state.

        Returns:
            True if pre-tool planning is enabled, False otherwise.
            Defaults to False if not set in config.
        """
        config_data = self.load()
        return bool(config_data.get('PRE_TOOL_PLANNING', False))

    def set_pre_tool_planning(self, enabled: bool) -> Optional[Path]:
        """Set the pre-tool planning enabled state.

        Args:
            enabled: True to enable pre-tool planning, False to disable.

        Returns:
            Backup path if backup was created, None otherwise.
        """
        return self.update_field('PRE_TOOL_PLANNING', enabled)

    def get_model_price(self, model_name: str) -> Dict[str, float]:
        """Get pricing for a specific model.

        Args:
            model_name: Model name (e.g., 'minimax/minimax-m2.5', 'GLM-4.7')

        Returns:
            Dict with 'in' and 'out' cost values per 1M tokens
        """
        config_data = self.load()
        model_prices = config_data.get('MODEL_PRICES', {})
        
        if model_name in model_prices:
            model_cost = model_prices[model_name]
            return {
                'in': float(model_cost.get('cost_in', 0.0)),
                'out': float(model_cost.get('cost_out', 0.0))
            }
        
        return {'in': 0.0, 'out': 0.0}

    def set_model_price(self, model_name: str, cost_in: float, cost_out: float) -> Optional[Path]:
        """Set pricing for a specific model.

        Args:
            model_name: Model name (e.g., 'minimax/minimax-m2.5', 'GLM-4.7')
            cost_in: Cost per 1M input tokens
            cost_out: Cost per 1M output tokens

        Returns:
            Backup path if backup was created, None otherwise
        """
        config_data = self.load()
        
        if 'MODEL_PRICES' not in config_data:
            config_data['MODEL_PRICES'] = {}
        
        config_data['MODEL_PRICES'][model_name] = {
            'cost_in': cost_in,
            'cost_out': cost_out
        }
        
        return self.save(config_data, create_backup=False)

    def list_model_prices(self) -> Dict[str, Dict[str, float]]:
        """Get all model-specific pricing.

        Returns:
            Dict mapping model names to their pricing (cost_in/cost_out per 1M tokens)
        """
        config_data = self.load()
        return config_data.get('MODEL_PRICES', {})

    def delete_model_price(self, model_name: str) -> Optional[Path]:
        """Delete pricing for a specific model.

        Args:
            model_name: Model name to remove from pricing

        Returns:
            Backup path if backup was created, None otherwise
        """
        config_data = self.load()
        
        if 'MODEL_PRICES' in config_data and model_name in config_data['MODEL_PRICES']:
            del config_data['MODEL_PRICES'][model_name]
            return self.save(config_data, create_backup=False)
        
        return None
