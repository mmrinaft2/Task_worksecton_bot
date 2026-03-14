import os
import re
import time
import hashlib
import requests
import logging
from urllib.parse import urlencode

logger = logging.getLogger(__name__)


class WorksectionAPI:
    def __init__(self):
        self.api_key = os.getenv('WORKSECTION_API_TOKEN') or os.getenv('WORKSECTION_API_KEY')
        domain = os.getenv('WS_ACCOUNT_DOMAIN') or os.getenv('WORKSECTION_ACCOUNT_URL', '')
        if domain and not domain.startswith('http'):
            domain = f"https://{domain}"
        self.account_url = domain.rstrip('/')
        self._last_request_time = 0

    @staticmethod
    def _strip_emoji(text: str) -> str:
        """Remove emoji characters that break Worksection hash"""
        emoji_pattern = re.compile(
            "[\U00010000-\U0010ffff"  # supplementary multilingual plane
            "\u2600-\u27bf"           # misc symbols
            "\u2b50-\u2b55"           # stars
            "\u23cf-\u23fa"           # misc technical
            "\u200d"                  # zero width joiner
            "\ufe0f"                  # variation selector
            "]+", flags=re.UNICODE)
        return emoji_pattern.sub('', text)

    def _make_hash(self, params: str) -> str:
        """Generate MD5 hash for authentication"""
        raw = params + self.api_key
        return hashlib.md5(raw.encode('utf-8')).hexdigest()

    def _rate_limit(self):
        """Ensure at least 1 second between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < 1.0:
            time.sleep(1.0 - elapsed)
        self._last_request_time = time.time()

    def _request(self, params: dict, files: dict = None) -> dict:
        """Make API request to Worksection"""
        if not self.api_key or not self.account_url:
            logger.error("Worksection API key or URL not configured")
            return {'status': 'error', 'message': 'API not configured'}

        self._rate_limit()

        # Hash = md5(plain_query_string + api_key)
        query_parts = [f"{k}={v}" for k, v in params.items()]
        query_str = '&'.join(query_parts)
        hash_value = self._make_hash(query_str)
        params['hash'] = hash_value

        # URL-encode params for the actual request URL
        encoded_url = f"{self.account_url}/api/admin/v2/?{urlencode(params)}"

        logger.info(f"WS API plain query (first 200): {query_str[:200]}")
        logger.info(f"WS API URL length: {len(encoded_url)}")

        try:
            if files:
                response = requests.post(encoded_url, files=files, timeout=30)
            else:
                response = requests.get(encoded_url, timeout=30)
            response.raise_for_status()
            result = response.json()
            logger.info(f"Worksection API response: {result}")
            return result
        except requests.exceptions.RequestException as e:
            logger.error(f"Worksection API request failed: {e}")
            return {'status': 'error', 'message': str(e)}

    def get_projects(self) -> dict:
        """Get list of active projects"""
        return self._request({'action': 'get_projects'})

    def post_task(self, id_project: int, title: str, text: str = '',
                  priority: int = 5, dateend: str = '', files: dict = None) -> dict:
        """Create a task in Worksection"""
        params = {
            'action': 'post_task',
            'id_project': str(id_project),
            'title': self._strip_emoji(title),
        }
        if text:
            params['text'] = self._strip_emoji(text)
        if priority:
            params['priority'] = str(priority)
        if dateend:
            params['dateend'] = dateend

        return self._request(params, files=files)

    def get_tasks(self, id_project: int, filter_status: str = '') -> dict:
        """Get list of tasks for a project"""
        params = {
            'action': 'get_tasks',
            'id_project': str(id_project),
        }
        if filter_status:
            params['filter'] = filter_status
        return self._request(params)

    def get_task(self, id_task: int) -> dict:
        """Get details of a specific task"""
        return self._request({
            'action': 'get_task',
            'id_task': str(id_task),
        })
