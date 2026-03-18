#!/bin/bash
set -e

echo "=== Generating Troubleshoot Support Bundle ==="

command -v kubectl >/dev/null 2>&1 || { echo "Error: kubectl is required."; exit 1; }

# Check if support-bundle plugin is available
if ! kubectl support-bundle --help >/dev/null 2>&1; then
    echo "Installing support-bundle kubectl plugin..."
    curl https://krew.sh/support-bundle | bash 2>/dev/null || {
        echo "Auto-install failed. Install manually:"
        echo "  https://troubleshoot.sh/docs/#installation"
        exit 1
    }
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT_DIR="$SCRIPT_DIR/../samples"
mkdir -p "$OUTPUT_DIR"

echo "Collecting support bundle..."
kubectl support-bundle --interactive=false \
    --output "$OUTPUT_DIR/sample-bundle.tar.gz" \
    - <<EOF
apiVersion: troubleshoot.sh/v1beta2
kind: SupportBundle
metadata:
  name: bundlescope-test
spec:
  collectors:
    - clusterInfo: {}
    - clusterResources: {}
    - logs:
        selector:
          - app=crash-loop
          - app=oom-victim
          - app=bad-image
          - app=unhealthy
          - app=healthy
        limits:
          maxLines: 10000
  analyzers: []
EOF

echo ""
echo "Bundle saved to: $OUTPUT_DIR/sample-bundle.tar.gz"
echo "Upload this to Bundlescope for analysis."
