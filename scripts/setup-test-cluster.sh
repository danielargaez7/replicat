#!/bin/bash
set -e

echo "=== Bundlescope Test Cluster Setup ==="
echo "Creates a kind cluster with intentional failures for demo purposes."
echo ""

# Check dependencies
command -v kind >/dev/null 2>&1 || { echo "Error: kind is required. Install from https://kind.sigs.k8s.io/"; exit 1; }
command -v kubectl >/dev/null 2>&1 || { echo "Error: kubectl is required."; exit 1; }

CLUSTER_NAME="bundlescope-test"

# Clean up existing cluster
if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "Deleting existing cluster..."
    kind delete cluster --name "$CLUSTER_NAME"
fi

echo "Creating kind cluster: $CLUSTER_NAME"
kind create cluster --name "$CLUSTER_NAME" --wait 60s

echo ""
echo "=== Deploying test workloads with intentional failures ==="

# 1. OOMKilled pod — memory limit too low for a stress workload
echo "[1/5] Deploying OOM pod..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: oom-victim
  namespace: default
  labels:
    app: oom-victim
    scenario: oom-kill
spec:
  containers:
  - name: stress
    image: polinux/stress
    command: ["stress"]
    args: ["--vm", "1", "--vm-bytes", "128M", "--vm-hang", "1"]
    resources:
      limits:
        memory: "50Mi"
      requests:
        memory: "50Mi"
EOF

# 2. CrashLoopBackOff — bad command
echo "[2/5] Deploying crash-loop pod..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: crash-loop-app
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: crash-loop
  template:
    metadata:
      labels:
        app: crash-loop
    spec:
      containers:
      - name: app
        image: busybox
        command: ["sh", "-c", "echo 'Starting app...' && sleep 2 && echo 'ERROR: Missing DB_HOST environment variable' >&2 && exit 1"]
        env:
        - name: APP_NAME
          value: "myapp"
EOF

# 3. ImagePullBackOff — nonexistent image
echo "[3/5] Deploying bad-image pod..."
kubectl apply -f - <<EOF
apiVersion: v1
kind: Pod
metadata:
  name: bad-image-pod
  namespace: default
  labels:
    app: bad-image
    scenario: image-pull
spec:
  containers:
  - name: app
    image: registry.example.com/nonexistent/image:v999
EOF

# 4. Failing liveness probe
echo "[4/5] Deploying failing-probe pod..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unhealthy-app
  namespace: default
spec:
  replicas: 1
  selector:
    matchLabels:
      app: unhealthy
  template:
    metadata:
      labels:
        app: unhealthy
    spec:
      containers:
      - name: app
        image: nginx:alpine
        ports:
        - containerPort: 80
        livenessProbe:
          httpGet:
            path: /healthz-does-not-exist
            port: 80
          initialDelaySeconds: 5
          periodSeconds: 3
          failureThreshold: 3
---
apiVersion: v1
kind: Service
metadata:
  name: unhealthy-svc
  namespace: default
spec:
  selector:
    app: unhealthy
  ports:
  - port: 80
    targetPort: 80
EOF

# 5. Healthy workload (for comparison)
echo "[5/5] Deploying healthy workload..."
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: healthy-app
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: healthy
  template:
    metadata:
      labels:
        app: healthy
    spec:
      containers:
      - name: nginx
        image: nginx:alpine
        ports:
        - containerPort: 80
        resources:
          requests:
            memory: "32Mi"
            cpu: "50m"
          limits:
            memory: "64Mi"
            cpu: "100m"
---
apiVersion: v1
kind: Service
metadata:
  name: healthy-svc
  namespace: default
spec:
  selector:
    app: healthy
  ports:
  - port: 80
    targetPort: 80
EOF

echo ""
echo "=== Waiting for failures to manifest (60 seconds) ==="
sleep 60

echo ""
echo "=== Current pod status ==="
kubectl get pods -A
echo ""
echo "=== Events ==="
kubectl get events --sort-by='.lastTimestamp' | tail -20
echo ""
echo "Test cluster ready. Run ./generate-bundle.sh to create a support bundle."
