"""
Worksection API Client
Authentication via MD5 hash: md5(query_params + api_key)
Base URL: https://{account}.worksection.com/api/admin/v2/
Rate limit: 1 request/sec
"""

import os
import hashlib
import logging
import time
from typing import Optional
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

WORKSECTION_API_KEY = os.getenv('WORKSECTION_API_KEY', '')
WORKSECTION_ACCOUNT_URL = os.getenv('WORKSECTION_ACCOUNT_URL', '').rstrip('/')


class WorksectionAPI:
    def __init__(self):
        self.api_key = WORKSECTION_API_KEY
        self.base_url = f"{WORKSECTION_ACCOUNT_URL}/api/admin/v2/"
        self._last_request_time = 0

    def _make_hash(self, query_params: str) -> str:
        """Calculate MD5 hash: md5(query_params + api_key)"""
        raw = query_params + self.api_key
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _rate_limit(self):
        """Ensure at least 1 second between requests"""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    def _request(self, params: dict) -> dict:
        """Make API request with hash authentication"""
        query_string = urlencode(params)
        hash_value = self._make_hash(query_string)
        params['hash'] = hash_value

        self._rate_limit()

        try:
            response = requests.get(self.base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                logger.error(f"Worksection API error: {data}")
            return data

        except requests.RequestException as e:
            logger.error(f"Worksection API request failed: {e}")
            return {'status': 'error', 'message': str(e)}

    def _post_request(self, params: dict, files: Optional[dict] = None) -> dict:
        """Make POST API request (for creating tasks with attachments)"""
        query_string = urlencode(params)
        hash_value = self._make_hash(query_string)
        params['hash'] = hash_value

        self._rate_limit()

        try:
            response = requests.post(
                self.base_url,
                data=params,
                files=files,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                logger.error(f"Worksection API error: {data}")
            return data

        except requests.RequestException as e:
            logger.error(f"Worksection API request failed: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_projects(self, filter_type: str = 'active') -> list:
        """Get list of projects"""
        result = self._request({
            'action': 'get_projects',
            'filter': filter_type,
        })
        if result.get('status') == 'ok':
            return result.get('data', [])
        return []

    def post_task(
        self,
        id_project: int,
        title: str,
        text: str = '',
        priority: int = 5,
        email_user_to: str = '',
        tags: str = '',
        dateend: str = '',
    ) -> dict:
        """Create a task in Worksection"""
        params = {
            'action': 'post_task',
            'id_project': id_project,
            'title': title,
        }
        if text:
            params['text'] = text
        if priority is not None:
            params['priority'] = priority
        if email_user_to:
            params['email_user_to'] = email_user_to
        if tags:
            params['tags'] = tags
        if dateend:
            params['dateend'] = dateend

        return self._post_request(params)

    def get_task(self, id_task: int) -> dict:
        """Get single task details"""
        result = self._request({
            'action': 'get_task',
            'id_task': id_task,
        })
        if result.get('status') == 'ok':
            return result.get('data', {})
        return {}
