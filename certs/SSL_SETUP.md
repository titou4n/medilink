# SSL/TLS Certificate Setup

## Overview
This directory should contain the SSL/TLS certificates and keys for HTTPS.

## Certificate Files
- `cert.pem` - SSL certificate
- `key.pem` - Private key

## Setup Options

### Option 1: Using Cloudflare (Recommended)
If using Cloudflare as your DNS provider:
1. Go to Cloudflare dashboard > SSL/TLS > Certificates
2. Generate an Origin Certificate or use Cloudflare's automatic HTTPS
3. Download the certificate and key
4. Save them as `cert.pem` and `key.pem` in this directory

### Option 2: Using Let's Encrypt with Certbot
```bash
# Install Certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d medilink.ltjs.net

# Copy certificates to this directory
sudo cp /etc/letsencrypt/live/medilink.ltjs.net/fullchain.pem cert.pem
sudo cp /etc/letsencrypt/live/medilink.ltjs.net/privkey.pem key.pem

# Fix permissions
sudo chown $USER:$USER cert.pem key.pem
chmod 600 key.pem
```

### Option 3: Self-Signed Certificate (Development Only)
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Docker Deployment
The certificates are mounted in the nginx container at:
- `/etc/nginx/ssl/cert.pem`
- `/etc/nginx/ssl/key.pem`

Ensure the files are present before starting the Docker containers.

## Security Notes
- Keep `key.pem` private and secure
- Never commit certificate files to version control
- Rotate certificates regularly (every 90 days for Let's Encrypt)
- The `key.pem` file should have restricted permissions (600)
