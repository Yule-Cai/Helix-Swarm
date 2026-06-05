"""Runtime configuration for Helix-Swarm."""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "helix_config.json"


class ConfigManager:
    def __init__(self):
        self.data = {
            "active": "local",
            "local": {
                "url": "http://localhost:1234/v1/chat/completions",
                "model": "local-model",
                "api_key": "not-needed",
            },
            "custom": {
                "url": "",
                "model": "",
                "api_key": "",
            },
            "theme": "dark",
            "lang": "zh",
            "total_tokens_used": 0,
            "keys_usage": {},
        }
        self.load()
        self.apply_env_overrides()

    def load(self):
        if CONFIG_PATH.exists():
            try:
                with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._deep_update(self.data, loaded)
            except json.JSONDecodeError:
                pass

    def _deep_update(self, target: dict, source: dict):
        for key, value in source.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value

    def apply_env_overrides(self):
        """Allow local shell environment to override checked-in config."""
        env_map = {
            ("local", "url"): "HELIX_LOCAL_URL",
            ("local", "model"): "HELIX_LOCAL_MODEL",
            ("local", "api_key"): "HELIX_LOCAL_API_KEY",
            ("custom", "url"): "HELIX_CUSTOM_URL",
            ("custom", "model"): "HELIX_CUSTOM_MODEL",
            ("custom", "api_key"): "HELIX_CUSTOM_API_KEY",
        }

        for (section, key), env_name in env_map.items():
            value = os.getenv(env_name)
            if value:
                self.data.setdefault(section, {})[key] = value

        active = os.getenv("HELIX_ACTIVE")
        if active in ("local", "custom"):
            self.data["active"] = active

    def save(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=4, ensure_ascii=False)

    def get_active(self):
        """获取当前激活的配置。"""
        active = self.data.get("active", "local")
        if active not in ("local", "custom"):
            active = "local"
            self.data["active"] = active
        self.data.setdefault(active, {})
        return self.data[active]

    def switch_to_local(self):
        """一键切回本地。"""
        self.data["active"] = "local"
        self.save()

    def switch_to_custom(self):
        """切换到云端。"""
        self.data["active"] = "custom"
        self.save()

    def update_custom(self, key, value):
        """更新云端配置项。"""
        self.data.setdefault("custom", {})[key] = value
        self.save()

    def update_local(self, key, value):
        """更新本地配置项。"""
        self.data.setdefault("local", {})[key] = value
        self.save()

    def update_active(self, key, value):
        """
        更新当前激活配置项。

        例如当前 active=local 时：
        /set model xxx 会写入 local.model，
        不会错误写入 custom.model。
        """
        active = self.data.get("active", "local")
        if active not in ("local", "custom"):
            active = "local"
            self.data["active"] = active
        self.data.setdefault(active, {})[key] = value
        self.save()


# 实例化单例
config = ConfigManager()