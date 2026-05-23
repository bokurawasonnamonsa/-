# Copy this file to cloudflare_dns_config.ps1 and fill values (never commit cloudflare_dns_config.ps1).

# Create token: Cloudflare Dashboard > My Profile > API Tokens > Create Token
# Use template "Edit zone DNS" and limit zone to 3301-svs.jp
$CF_API_TOKEN = "paste_token_here"

# Apex A record: usually name is your domain exactly
$CF_ZONE_NAME   = "3301-svs.jp"
$CF_RECORD_NAME = "3301-svs.jp"
$CF_TARGET_IP   = "160.251.140.31"

# Optional: Cloudflare TLS to origin — use "full" after VPS deploy with self-signed cert (see UPDATE_CLOUDFLARE_SSL.bat).
# Requires token permission Zone > SSL Settings > Edit. Values: flexible | full | strict | off
# $CF_SSL_MODE = "full"
