#!/usr/bin/env python3
"""
TASK-009: Generate SSL certificates for HTTPS

This script generates SSL certificates for the Road Trip application:
1. Let's Encrypt certificates for production
2. Self-signed certificates for development
3. Certificate renewal automation
4. Multi-domain support

Usage:
    python scripts/generate_ssl_certificates.py --env production --domain roadtrip.app
    python scripts/generate_ssl_certificates.py --env development
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SSLCertificateManager:
    """Manages SSL certificate generation and renewal"""
    
    def __init__(self, environment: str = 'production'):
        self.environment = environment
        self.cert_dir = Path('/etc/letsencrypt/live') if environment == 'production' else Path('./certs')
        self.cert_dir.mkdir(parents=True, exist_ok=True)
        
        # Certificate paths
        self.paths = {
            'privkey': 'privkey.pem',
            'fullchain': 'fullchain.pem',
            'cert': 'cert.pem',
            'chain': 'chain.pem'
        }
        
        # Supported domains
        self.domains = {
            'production': [
                'roadtrip.app',
                'www.roadtrip.app',
                'api.roadtrip.app',
                'admin.roadtrip.app'
            ],
            'staging': [
                'staging.roadtrip.app',
                'api-staging.roadtrip.app'
            ],
            'development': [
                'localhost',
                'roadtrip.local',
                'api.roadtrip.local'
            ]
        }
        
    def generate_production_certificates(self, domains: List[str], email: str) -> bool:
        """Generate Let's Encrypt certificates for production"""
        logger.info(f"Generating Let's Encrypt certificates for domains: {domains}")
        
        try:
            # Check if certbot is installed
            result = subprocess.run(['which', 'certbot'], capture_output=True)
            if result.returncode != 0:
                logger.error("Certbot is not installed. Please install certbot first.")
                logger.info("Run: sudo apt-get update && sudo apt-get install certbot")
                return False
            
            # Build certbot command
            cmd = [
                'sudo', 'certbot', 'certonly',
                '--standalone',
                '--non-interactive',
                '--agree-tos',
                '--email', email,
                '--no-eff-email'
            ]
            
            # Add domains
            for domain in domains:
                cmd.extend(['-d', domain])
            
            # Add staging flag for testing
            if self.environment == 'staging':
                cmd.append('--staging')
            
            # Execute certbot
            logger.info(f"Running certbot command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info("✅ Successfully generated Let's Encrypt certificates")
                self._verify_certificates(domains[0])
                return True
            else:
                logger.error(f"Certbot failed: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to generate production certificates: {e}")
            return False
            
    def generate_self_signed_certificate(self, domains: List[str]) -> bool:
        """Generate self-signed certificates for development"""
        logger.info(f"Generating self-signed certificates for domains: {domains}")
        
        try:
            primary_domain = domains[0]
            cert_path = self.cert_dir / primary_domain
            cert_path.mkdir(parents=True, exist_ok=True)
            
            # Generate private key
            privkey_path = cert_path / self.paths['privkey']
            cmd_key = [
                'openssl', 'genrsa',
                '-out', str(privkey_path),
                '2048'
            ]
            
            logger.info("Generating private key...")
            subprocess.run(cmd_key, check=True)
            
            # Create config file for multiple domains
            config_content = self._create_openssl_config(domains)
            config_path = cert_path / 'openssl.cnf'
            with open(config_path, 'w') as f:
                f.write(config_content)
            
            # Generate certificate
            cert_file_path = cert_path / self.paths['cert']
            cmd_cert = [
                'openssl', 'req',
                '-new',
                '-x509',
                '-key', str(privkey_path),
                '-out', str(cert_file_path),
                '-days', '365',
                '-config', str(config_path)
            ]
            
            logger.info("Generating self-signed certificate...")
            subprocess.run(cmd_cert, check=True)
            
            # Copy cert to fullchain for compatibility
            fullchain_path = cert_path / self.paths['fullchain']
            subprocess.run(['cp', str(cert_file_path), str(fullchain_path)], check=True)
            
            # Create empty chain file
            chain_path = cert_path / self.paths['chain']
            chain_path.touch()
            
            logger.info(f"✅ Successfully generated self-signed certificates in {cert_path}")
            self._verify_certificates(primary_domain)
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate self-signed certificate: {e}")
            return False
            
    def _create_openssl_config(self, domains: List[str]) -> str:
        """Create OpenSSL configuration for multiple domains"""
        san_entries = [f"DNS.{i+1} = {domain}" for i, domain in enumerate(domains)]
        san_section = '\n'.join(san_entries)
        
        return f"""
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = v3_req

[dn]
C = US
ST = California
L = San Francisco
O = Road Trip App
OU = Development
CN = {domains[0]}

[v3_req]
subjectAltName = @alt_names

[alt_names]
{san_section}
"""
    
    def setup_auto_renewal(self, email: str) -> bool:
        """Set up automatic certificate renewal"""
        logger.info("Setting up automatic certificate renewal...")
        
        try:
            # Create renewal script
            renewal_script = """#!/bin/bash
# Road Trip SSL Certificate Renewal Script

LOGFILE="/var/log/roadtrip-ssl-renewal.log"
EMAIL="{email}"

echo "$(date): Starting SSL certificate renewal" >> $LOGFILE

# Renew certificates
certbot renew --quiet --no-self-upgrade >> $LOGFILE 2>&1

# Check if renewal was successful
if [ $? -eq 0 ]; then
    echo "$(date): Certificate renewal successful" >> $LOGFILE
    
    # Reload nginx if it's running
    if systemctl is-active --quiet nginx; then
        systemctl reload nginx
        echo "$(date): Nginx reloaded" >> $LOGFILE
    fi
    
    # Reload the application
    if systemctl is-active --quiet roadtrip-api; then
        systemctl reload roadtrip-api
        echo "$(date): Road Trip API reloaded" >> $LOGFILE
    fi
else
    echo "$(date): Certificate renewal failed" >> $LOGFILE
    # Send alert email
    echo "SSL certificate renewal failed. Please check logs." | mail -s "Road Trip SSL Renewal Failed" $EMAIL
fi
"""
            
            # Write renewal script
            renewal_script_path = Path('/opt/roadtrip/ssl-renewal.sh')
            renewal_script_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(renewal_script_path, 'w') as f:
                f.write(renewal_script.format(email=email))
            
            # Make executable
            os.chmod(renewal_script_path, 0o755)
            
            # Add to crontab
            cron_entry = f"0 3 * * * /opt/roadtrip/ssl-renewal.sh\n"
            
            # Check if entry already exists
            result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
            if result.returncode == 0 and '/opt/roadtrip/ssl-renewal.sh' not in result.stdout:
                # Add new cron entry
                current_cron = result.stdout
                new_cron = current_cron + cron_entry
                
                process = subprocess.Popen(['crontab', '-'], stdin=subprocess.PIPE, text=True)
                process.communicate(input=new_cron)
                
                logger.info("✅ Added cron job for automatic renewal (daily at 3 AM)")
            else:
                logger.info("Cron job already exists")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to set up auto-renewal: {e}")
            return False
            
    def _verify_certificates(self, domain: str) -> bool:
        """Verify generated certificates"""
        logger.info(f"Verifying certificates for {domain}...")
        
        try:
            cert_path = self.cert_dir / domain
            
            # Check if all required files exist
            for file_type, filename in self.paths.items():
                file_path = cert_path / filename
                if not file_path.exists():
                    logger.warning(f"Missing {file_type}: {file_path}")
                    return False
                else:
                    logger.info(f"✓ Found {file_type}: {file_path}")
            
            # Verify certificate details
            cert_file = cert_path / self.paths['cert']
            cmd = ['openssl', 'x509', '-in', str(cert_file), '-text', '-noout']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse certificate info
                cert_info = result.stdout
                
                # Check expiration
                cmd_dates = ['openssl', 'x509', '-in', str(cert_file), '-dates', '-noout']
                dates_result = subprocess.run(cmd_dates, capture_output=True, text=True)
                
                if dates_result.returncode == 0:
                    logger.info("Certificate dates:")
                    for line in dates_result.stdout.strip().split('\n'):
                        logger.info(f"  {line}")
                
                # Check domains
                if domain in cert_info:
                    logger.info(f"✅ Certificate is valid for {domain}")
                    return True
                else:
                    logger.warning(f"Certificate does not include {domain}")
                    return False
            else:
                logger.error(f"Failed to verify certificate: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Certificate verification failed: {e}")
            return False
            
    def backup_certificates(self, domain: str) -> Optional[str]:
        """Backup existing certificates before renewal"""
        logger.info(f"Backing up certificates for {domain}...")
        
        try:
            cert_path = self.cert_dir / domain
            if not cert_path.exists():
                logger.warning(f"No certificates found for {domain}")
                return None
            
            # Create backup directory
            backup_dir = Path('/opt/roadtrip/ssl-backups')
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create timestamped backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{domain}_{timestamp}.tar.gz"
            backup_path = backup_dir / backup_name
            
            # Create tarball
            cmd = ['tar', '-czf', str(backup_path), '-C', str(self.cert_dir), domain]
            subprocess.run(cmd, check=True)
            
            logger.info(f"✅ Backed up certificates to {backup_path}")
            return str(backup_path)
            
        except Exception as e:
            logger.error(f"Failed to backup certificates: {e}")
            return None
            
    def generate_dhparam(self, bits: int = 2048) -> bool:
        """Generate Diffie-Hellman parameters for enhanced security"""
        logger.info(f"Generating {bits}-bit DH parameters...")
        
        try:
            dhparam_path = self.cert_dir / 'dhparam.pem'
            
            if dhparam_path.exists():
                logger.info("DH parameters already exist")
                return True
            
            cmd = ['openssl', 'dhparam', '-out', str(dhparam_path), str(bits)]
            
            logger.info("This may take several minutes...")
            subprocess.run(cmd, check=True)
            
            logger.info(f"✅ Generated DH parameters: {dhparam_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to generate DH parameters: {e}")
            return False
            
    def export_certificates_for_gcp(self, domain: str) -> Dict[str, str]:
        """Export certificates in format suitable for GCP load balancers"""
        logger.info(f"Exporting certificates for GCP load balancer...")
        
        try:
            cert_path = self.cert_dir / domain
            
            # Read certificate files
            with open(cert_path / self.paths['cert'], 'r') as f:
                cert_content = f.read()
            
            with open(cert_path / self.paths['privkey'], 'r') as f:
                key_content = f.read()
            
            with open(cert_path / self.paths['chain'], 'r') as f:
                chain_content = f.read()
            
            # Create GCP-compatible format
            gcp_cert = {
                'certificate': cert_content,
                'private_key': key_content,
                'certificate_chain': chain_content if chain_content else None
            }
            
            # Save as JSON for easy import
            export_path = cert_path / 'gcp_certificate.json'
            with open(export_path, 'w') as f:
                json.dump(gcp_cert, f, indent=2)
            
            logger.info(f"✅ Exported certificates to {export_path}")
            
            # Also create upload commands
            commands = f"""
# Upload certificate to GCP
gcloud compute ssl-certificates create roadtrip-ssl-cert \\
    --certificate={cert_path / self.paths['cert']} \\
    --private-key={cert_path / self.paths['privkey']} \\
    --project=roadtrip-prod

# Attach to load balancer
gcloud compute target-https-proxies update roadtrip-https-proxy \\
    --ssl-certificates=roadtrip-ssl-cert \\
    --project=roadtrip-prod
"""
            
            commands_path = cert_path / 'gcp_upload_commands.sh'
            with open(commands_path, 'w') as f:
                f.write(commands)
            
            os.chmod(commands_path, 0o755)
            logger.info(f"Created GCP upload commands: {commands_path}")
            
            return gcp_cert
            
        except Exception as e:
            logger.error(f"Failed to export certificates: {e}")
            return {}


def main():
    parser = argparse.ArgumentParser(description="Generate SSL certificates for Road Trip")
    parser.add_argument('--env', choices=['production', 'staging', 'development'], 
                       default='production', help='Environment to generate certificates for')
    parser.add_argument('--domains', nargs='+', help='Domains to generate certificates for')
    parser.add_argument('--email', help='Email for Let\'s Encrypt notifications')
    parser.add_argument('--self-signed', action='store_true', 
                       help='Generate self-signed certificates')
    parser.add_argument('--renew', action='store_true', 
                       help='Renew existing certificates')
    parser.add_argument('--setup-renewal', action='store_true', 
                       help='Set up automatic renewal')
    parser.add_argument('--backup', action='store_true', 
                       help='Backup existing certificates')
    parser.add_argument('--export-gcp', action='store_true', 
                       help='Export certificates for GCP')
    parser.add_argument('--dhparam', action='store_true', 
                       help='Generate DH parameters')
    
    args = parser.parse_args()
    
    # Create certificate manager
    manager = SSLCertificateManager(args.env)
    
    # Determine domains
    if args.domains:
        domains = args.domains
    else:
        domains = manager.domains.get(args.env, ['localhost'])
    
    logger.info(f"Working with domains: {domains}")
    
    # Backup existing certificates if requested
    if args.backup and domains:
        backup_path = manager.backup_certificates(domains[0])
        if backup_path:
            logger.info(f"Certificates backed up to: {backup_path}")
    
    # Generate certificates
    if args.self_signed or args.env == 'development':
        success = manager.generate_self_signed_certificate(domains)
    else:
        if not args.email:
            logger.error("Email is required for Let's Encrypt certificates")
            sys.exit(1)
        success = manager.generate_production_certificates(domains, args.email)
    
    if not success:
        logger.error("Certificate generation failed")
        sys.exit(1)
    
    # Generate DH parameters if requested
    if args.dhparam:
        manager.generate_dhparam()
    
    # Set up auto-renewal if requested
    if args.setup_renewal and args.email:
        manager.setup_auto_renewal(args.email)
    
    # Export for GCP if requested
    if args.export_gcp and domains:
        manager.export_certificates_for_gcp(domains[0])
    
    logger.info("✅ SSL certificate generation completed successfully")
    
    # Print next steps
    print("\n" + "="*60)
    print("NEXT STEPS:")
    print("="*60)
    
    if args.env == 'production':
        print("1. Update your web server configuration to use the new certificates")
        print(f"   - Certificate: /etc/letsencrypt/live/{domains[0]}/fullchain.pem")
        print(f"   - Private Key: /etc/letsencrypt/live/{domains[0]}/privkey.pem")
        print("2. Reload your web server:")
        print("   - Nginx: sudo systemctl reload nginx")
        print("   - Apache: sudo systemctl reload apache2")
        print("3. Test your SSL configuration:")
        print(f"   - https://www.ssllabs.com/ssltest/analyze.html?d={domains[0]}")
    else:
        print("1. Trust the self-signed certificate in your browser")
        print(f"2. Certificate location: {manager.cert_dir}/{domains[0]}/")
        print("3. Add to your hosts file:")
        for domain in domains:
            if domain != 'localhost':
                print(f"   127.0.0.1  {domain}")


if __name__ == "__main__":
    main()