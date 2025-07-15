#!/bin/bash
# Script to generate or obtain SSL certificates for production

set -e

echo "=== SSL/TLS Certificate Setup for AI Road Trip Storyteller ==="
echo

# Configuration
DOMAIN="${DOMAIN:-api.roadtrip.app}"
EMAIL="${EMAIL:-admin@roadtrip.app}"
CERT_DIR="${CERT_DIR:-/etc/letsencrypt/live/$DOMAIN}"
NGINX_SSL_DIR="/etc/nginx/ssl"

# Function to check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        echo "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to install certbot if not present
install_certbot() {
    if ! command -v certbot &> /dev/null; then
        echo "Installing Certbot..."
        apt-get update
        apt-get install -y certbot python3-certbot-nginx
    else
        echo "✓ Certbot is already installed"
    fi
}

# Function to generate self-signed certificate (for testing)
generate_self_signed() {
    echo "Generating self-signed certificate for testing..."
    
    mkdir -p $NGINX_SSL_DIR
    
    # Generate private key
    openssl genrsa -out $NGINX_SSL_DIR/privkey.pem 2048
    
    # Generate certificate signing request
    openssl req -new -key $NGINX_SSL_DIR/privkey.pem \
        -out $NGINX_SSL_DIR/cert.csr \
        -subj "/C=US/ST=State/L=City/O=AI Road Trip Storyteller/CN=$DOMAIN"
    
    # Generate self-signed certificate
    openssl x509 -req -days 365 -in $NGINX_SSL_DIR/cert.csr \
        -signkey $NGINX_SSL_DIR/privkey.pem \
        -out $NGINX_SSL_DIR/fullchain.pem
    
    # Copy as chain (self-signed doesn't have a chain)
    cp $NGINX_SSL_DIR/fullchain.pem $NGINX_SSL_DIR/chain.pem
    
    # Set permissions
    chmod 600 $NGINX_SSL_DIR/privkey.pem
    chmod 644 $NGINX_SSL_DIR/fullchain.pem
    chmod 644 $NGINX_SSL_DIR/chain.pem
    
    echo "✓ Self-signed certificate generated"
    echo "  Location: $NGINX_SSL_DIR"
    echo "  ⚠️  Warning: This certificate is for testing only!"
}

# Function to generate Let's Encrypt certificate
generate_letsencrypt() {
    echo "Generating Let's Encrypt certificate..."
    
    # Check if domain is pointing to this server
    echo "Checking domain configuration..."
    SERVER_IP=$(curl -s http://ipinfo.io/ip)
    DOMAIN_IP=$(dig +short $DOMAIN | tail -n1)
    
    if [[ "$SERVER_IP" != "$DOMAIN_IP" ]]; then
        echo "⚠️  Warning: Domain $DOMAIN is not pointing to this server"
        echo "  Server IP: $SERVER_IP"
        echo "  Domain IP: $DOMAIN_IP"
        echo "  Please update DNS records before continuing."
        read -p "Continue anyway? (y/N): " continue_anyway
        if [[ ! $continue_anyway =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Stop nginx temporarily
    echo "Stopping nginx..."
    systemctl stop nginx || true
    
    # Generate certificate
    certbot certonly --standalone \
        --non-interactive \
        --agree-tos \
        --email $EMAIL \
        --domains $DOMAIN \
        --keep-until-expiring
    
    # Create symbolic links in nginx directory
    mkdir -p $NGINX_SSL_DIR
    ln -sf $CERT_DIR/privkey.pem $NGINX_SSL_DIR/privkey.pem
    ln -sf $CERT_DIR/fullchain.pem $NGINX_SSL_DIR/fullchain.pem
    ln -sf $CERT_DIR/chain.pem $NGINX_SSL_DIR/chain.pem
    
    # Start nginx
    echo "Starting nginx..."
    systemctl start nginx
    
    echo "✓ Let's Encrypt certificate generated"
    echo "  Location: $CERT_DIR"
    
    # Set up auto-renewal
    setup_auto_renewal
}

# Function to set up auto-renewal
setup_auto_renewal() {
    echo "Setting up auto-renewal..."
    
    # Create renewal hook script
    cat > /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh << 'EOF'
#!/bin/bash
nginx -t && systemctl reload nginx
EOF
    
    chmod +x /etc/letsencrypt/renewal-hooks/deploy/nginx-reload.sh
    
    # Test renewal
    certbot renew --dry-run
    
    echo "✓ Auto-renewal configured"
    echo "  Certificates will be renewed automatically when needed"
}

# Function to import existing certificate
import_certificate() {
    echo "Importing existing certificate..."
    
    read -p "Path to certificate file (fullchain.pem): " cert_path
    read -p "Path to private key file (privkey.pem): " key_path
    read -p "Path to chain file (chain.pem) [optional]: " chain_path
    
    if [[ ! -f "$cert_path" || ! -f "$key_path" ]]; then
        echo "Error: Certificate or key file not found"
        exit 1
    fi
    
    # Create directory and copy files
    mkdir -p $NGINX_SSL_DIR
    cp "$cert_path" $NGINX_SSL_DIR/fullchain.pem
    cp "$key_path" $NGINX_SSL_DIR/privkey.pem
    
    if [[ -f "$chain_path" ]]; then
        cp "$chain_path" $NGINX_SSL_DIR/chain.pem
    else
        # Extract chain from fullchain
        openssl x509 -in $NGINX_SSL_DIR/fullchain.pem -out $NGINX_SSL_DIR/chain.pem
    fi
    
    # Set permissions
    chmod 600 $NGINX_SSL_DIR/privkey.pem
    chmod 644 $NGINX_SSL_DIR/fullchain.pem
    chmod 644 $NGINX_SSL_DIR/chain.pem
    
    echo "✓ Certificate imported successfully"
}

# Function to verify certificate
verify_certificate() {
    echo "Verifying certificate configuration..."
    
    # Check certificate validity
    openssl x509 -in $NGINX_SSL_DIR/fullchain.pem -noout -dates
    
    # Check certificate matches private key
    cert_modulus=$(openssl x509 -in $NGINX_SSL_DIR/fullchain.pem -noout -modulus | md5sum)
    key_modulus=$(openssl rsa -in $NGINX_SSL_DIR/privkey.pem -noout -modulus | md5sum)
    
    if [[ "$cert_modulus" == "$key_modulus" ]]; then
        echo "✓ Certificate and private key match"
    else
        echo "✗ Certificate and private key do NOT match!"
        exit 1
    fi
    
    # Test nginx configuration
    if command -v nginx &> /dev/null; then
        nginx -t
        echo "✓ Nginx configuration is valid"
    fi
}

# Function to generate Diffie-Hellman parameters
generate_dhparam() {
    echo "Generating Diffie-Hellman parameters (this may take a while)..."
    
    if [[ ! -f $NGINX_SSL_DIR/dhparam.pem ]]; then
        openssl dhparam -out $NGINX_SSL_DIR/dhparam.pem 2048
        echo "✓ DH parameters generated"
    else
        echo "✓ DH parameters already exist"
    fi
}

# Main menu
main_menu() {
    echo "SSL/TLS Certificate Setup Options:"
    echo "1) Generate Let's Encrypt certificate (Production)"
    echo "2) Generate self-signed certificate (Testing)"
    echo "3) Import existing certificate"
    echo "4) Verify current certificate"
    echo "5) Generate DH parameters only"
    echo "6) Exit"
    
    read -p "Select option (1-6): " option
    
    case $option in
        1)
            check_root
            install_certbot
            generate_letsencrypt
            generate_dhparam
            verify_certificate
            ;;
        2)
            generate_self_signed
            generate_dhparam
            verify_certificate
            ;;
        3)
            import_certificate
            generate_dhparam
            verify_certificate
            ;;
        4)
            verify_certificate
            ;;
        5)
            generate_dhparam
            ;;
        6)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option"
            exit 1
            ;;
    esac
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --domain)
            DOMAIN="$2"
            shift 2
            ;;
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --self-signed)
            generate_self_signed
            generate_dhparam
            verify_certificate
            exit 0
            ;;
        --letsencrypt)
            check_root
            install_certbot
            generate_letsencrypt
            generate_dhparam
            verify_certificate
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run main menu if no arguments
main_menu

echo
echo "=== SSL/TLS Setup Complete ==="
echo "Next steps:"
echo "1. Update nginx configuration to use SSL"
echo "2. Restart nginx: systemctl restart nginx"
echo "3. Test SSL configuration: https://www.ssllabs.com/ssltest/"
echo
echo "For production, ensure:"
echo "- Firewall allows port 443"
echo "- Domain DNS is correctly configured"
echo "- Auto-renewal is working (for Let's Encrypt)"