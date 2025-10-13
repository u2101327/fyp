#!/usr/bin/env python3
"""
LeakGuard API Client Example
This script demonstrates how to interact with the LeakGuard API
"""

import requests
import json
from datetime import datetime, timedelta

class LeakGuardClient:
    def __init__(self, base_url="http://localhost:8000/api", token=None):
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Token {token}" if token else None,
            "Content-Type": "application/json"
        }
    
    def _make_request(self, method, endpoint, data=None, params=None):
        """Make HTTP request to API"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API Error: {e}")
            return None
    
    # User Management
    def get_profile(self):
        """Get user profile"""
        return self._make_request("GET", "/profile/")
    
    def update_profile(self, data):
        """Update user profile"""
        return self._make_request("PATCH", "/profile/", data=data)
    
    # Data Sources
    def get_sources(self):
        """Get all data sources"""
        return self._make_request("GET", "/sources/")
    
    def create_source(self, name, source_type, url=None, configuration=None):
        """Create a new data source"""
        data = {
            "name": name,
            "source_type": source_type,
            "url": url,
            "configuration": configuration or {}
        }
        return self._make_request("POST", "/sources/", data=data)
    
    # Monitored Credentials
    def get_credentials(self):
        """Get all monitored credentials"""
        return self._make_request("GET", "/credentials/")
    
    def create_credential(self, credential_type, value, tags=None, notes=None):
        """Create a new monitored credential"""
        data = {
            "credential_type": credential_type,
            "value": value,
            "tags": tags or [],
            "notes": notes or ""
        }
        return self._make_request("POST", "/credentials/", data=data)
    
    def bulk_create_credentials(self, credentials):
        """Bulk create multiple credentials"""
        data = {"credentials": credentials}
        return self._make_request("POST", "/credentials/bulk/", data=data)
    
    # Credential Leaks
    def get_leaks(self, **filters):
        """Get credential leaks with optional filters"""
        return self._make_request("GET", "/leaks/", params=filters)
    
    def search_leaks(self, query, **filters):
        """Search for leaks"""
        params = {"q": query, **filters}
        return self._make_request("GET", "/leaks/search/", params=params)
    
    def create_leak(self, leak_data):
        """Create a new credential leak"""
        return self._make_request("POST", "/leaks/", data=leak_data)
    
    def bulk_update_leaks(self, leak_ids, status=None, severity=None):
        """Bulk update multiple leaks"""
        data = {
            "leak_ids": leak_ids,
            "status": status,
            "severity": severity
        }
        return self._make_request("PATCH", "/leaks/bulk-update/", data=data)
    
    # Alerts
    def get_alerts(self, **filters):
        """Get alerts with optional filters"""
        return self._make_request("GET", "/alerts/", params=filters)
    
    def mark_alerts_read(self, alert_ids=None):
        """Mark alerts as read"""
        data = {"alert_ids": alert_ids} if alert_ids else {}
        return self._make_request("POST", "/alerts/mark-read/", data=data)
    
    # Monitoring
    def start_monitoring(self, source_id, configuration=None):
        """Start monitoring a data source"""
        data = {
            "source_id": source_id,
            "configuration": configuration or {}
        }
        return self._make_request("POST", "/monitoring/start/", data=data)
    
    def stop_monitoring(self, session_id):
        """Stop a monitoring session"""
        data = {"session_id": session_id}
        return self._make_request("POST", "/monitoring/stop/", data=data)
    
    # Analytics
    def get_dashboard_stats(self):
        """Get dashboard statistics"""
        return self._make_request("GET", "/dashboard/stats/")
    
    def get_leak_analytics(self):
        """Get leak analytics"""
        return self._make_request("GET", "/analytics/leaks/")
    
    def get_source_analytics(self):
        """Get source analytics"""
        return self._make_request("GET", "/analytics/sources/")


def main():
    """Example usage of the LeakGuard API client"""
    
    # Initialize client (replace with your actual token)
    client = LeakGuardClient(token="your_api_token_here")
    
    print("=== LeakGuard API Client Example ===\n")
    
    # 1. Get user profile
    print("1. Getting user profile...")
    profile = client.get_profile()
    if profile:
        print(f"   User: {profile['user']['username']}")
        print(f"   Email notifications: {profile['email_notifications']}")
    
    # 2. Get dashboard stats
    print("\n2. Getting dashboard statistics...")
    stats = client.get_dashboard_stats()
    if stats:
        print(f"   Total monitored credentials: {stats['total_monitored_credentials']}")
        print(f"   Total leaks: {stats['total_leaks']}")
        print(f"   Critical leaks: {stats['critical_leaks']}")
        print(f"   Unread alerts: {stats['unread_alerts']}")
    
    # 3. Create a monitored credential
    print("\n3. Creating monitored credential...")
    credential = client.create_credential(
        credential_type="email",
        value="test@example.com",
        tags=["test", "demo"],
        notes="Test credential for demo"
    )
    if credential:
        print(f"   Created credential ID: {credential['id']}")
    
    # 4. Bulk create credentials
    print("\n4. Bulk creating credentials...")
    credentials_data = [
        {
            "credential_type": "username",
            "value": "testuser123",
            "tags": ["social", "test"]
        },
        {
            "credential_type": "domain",
            "value": "example.com",
            "tags": ["work", "critical"]
        }
    ]
    bulk_result = client.bulk_create_credentials(credentials_data)
    if bulk_result:
        print(f"   Created {len(bulk_result)} credentials")
    
    # 5. Get all credentials
    print("\n5. Getting all monitored credentials...")
    credentials = client.get_credentials()
    if credentials:
        print(f"   Found {len(credentials['results'])} credentials")
        for cred in credentials['results'][:3]:  # Show first 3
            print(f"   - {cred['credential_type']}: {cred['value']}")
    
    # 6. Search for leaks
    print("\n6. Searching for leaks...")
    leaks = client.search_leaks("password", severity="high")
    if leaks:
        print(f"   Found {len(leaks)} high-severity leaks containing 'password'")
    
    # 7. Get recent alerts
    print("\n7. Getting recent alerts...")
    alerts = client.get_alerts()
    if alerts:
        print(f"   Found {len(alerts['results'])} alerts")
        for alert in alerts['results'][:3]:  # Show first 3
            print(f"   - {alert['title']} ({alert['priority']})")
    
    # 8. Get leak analytics
    print("\n8. Getting leak analytics...")
    analytics = client.get_leak_analytics()
    if analytics:
        print("   Leaks by severity:")
        for severity, count in analytics['leaks_by_severity'].items():
            print(f"     {severity}: {count}")
        
        print("   Leaks by source:")
        for source, count in analytics['leaks_by_source'].items():
            print(f"     {source}: {count}")
    
    # 9. Get data sources
    print("\n9. Getting data sources...")
    sources = client.get_sources()
    if sources:
        print(f"   Found {len(sources['results'])} data sources")
        for source in sources['results']:
            print(f"   - {source['name']} ({source['source_type']})")
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    main()
