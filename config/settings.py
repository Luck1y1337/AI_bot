import os
from pydantic import BaseModel, field_validator
from typing import List
from dotenv import dotenv_values

class Settings(BaseModel):
    TELEGRAM_TOKEN: str
    MISTRAL_API_KEY: str
    ADMIN_USER_IDS: List[int]
    ADMIN_PANEL_TOKEN: str
    ENABLE_WHITELIST: bool
    WHITELIST_USER_IDS: List[int]
    BLACKLIST_USER_IDS: List[int]

    @field_validator('ADMIN_USER_IDS', 'WHITELIST_USER_IDS', 'BLACKLIST_USER_IDS', mode='before')
    @classmethod
    def parse_comma_separated_ints(cls, v):
        if isinstance(v, str):
            return [int(x.strip()) for x in v.split(',') if x.strip()]
        if v is None:
            return []
        return v

    @field_validator('TELEGRAM_TOKEN', 'MISTRAL_API_KEY', 'ADMIN_PANEL_TOKEN')
    @classmethod
    def check_placeholders(cls, v, info):
        if 'changeme' in v.lower() or 'your_' in v.lower():
            raise ValueError(f"{info.field_name} must be changed from the placeholder value.")
        return v

def get_settings() -> Settings:
    env_vars = dotenv_values(".env")
    for k, v in os.environ.items():
        if k in Settings.model_fields:
            env_vars[k] = v
            
    if 'ENABLE_WHITELIST' not in env_vars:
        env_vars['ENABLE_WHITELIST'] = 'true'
    if 'BLACKLIST_USER_IDS' not in env_vars or env_vars['BLACKLIST_USER_IDS'] is None:
        env_vars['BLACKLIST_USER_IDS'] = ''
        
    return Settings(**env_vars)
