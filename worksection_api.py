import os
import time
import hashlib
import requests
import logging

logger = logging.getLogger(__name__)


class WorksectionAPI:
    def __init__(self):
        self.api_key = os.getenv('WORKSECTION_API_TOKEN') or os.getenv('WORKSECTION_API_KEY')
        domain = os.getenv('WS_ACCOUNT_DOMAIN') or os.getenv('WORKSECTION_ACCOUNT_URL', '')
        if domain and not domain.startswith('http'):
            domain = f"https://{domain}"
        self.account_url = domain.rstrip('/')
        self._last_request_time = 0

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

        # Build query string for hash (without files)
        query_parts = [f"{k}={v}" for k, v in sorted(params.items())]
        query_str = '&'.join(query_parts)
        params['hash'] = self._make_hash(query_str)

        url = f"{self.account_url}/api/admin/v2/"

        try:
            if files:
                response = requests.post(url, data=params, files=files, timeout=30)
            else:
                response = requests.post(url, data=params, timeout=30)
            response.raise_for_status()
            return response.json()
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
            'title': title,
        }
        if text:
            params['text'] = text
        if priority:
            params['priority'] = str(priority)
        if dateend:
            params['dateend'] = dateend

        return self._request(params, files=files)
