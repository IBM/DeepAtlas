# Microservices on CloudLab

The following experiment setup is based on the c6420 node on Cloudlab. It should also work on other machines with minimal changes, as long as the OS is Ubuntu 20.04 LTS and an additional block device named `sdb`.
* 72 nodes (Intel Skylake, 32 core, 2 disk)
* CPU: Two Sixteen-core Intel Xeon Gold 6142 CPUs at 2.6 GHz
* RAM: 384GB ECC DDR4-2666 Memory
* Disk: Two Seagate 1TB 7200 RPM 6G SATA HDs
* NIC: Dual-port Intel X710 10Gbe NIC
* Image: emulab-ops/UBUNTU20-64-STD	

## Prerequisites

### Check Unformatted Block Devices
1. Ensure there is a block device with no partition
```
lsblk
```
```
sdb      8:16   0 931.5G  0 disk 
├─sdb1   8:17   0 931.5G  0 part 
└─sdb9   8:25   0     8M  0 part 
```
2. Erase the device if it is not formatted (e.g., the sdb above)
```
sudo wipefs -fa /dev/sdb1 && sudo wipefs -fa /dev/sdb9 && sudo wipefs -fa /dev/sdb
```

### Create Extra Disk Space for Containers
1. Create a directory
```
sudo mkdir /data
```
2. Mount the available disk space to the directory
```
sudo /usr/local/etc/emulab/mkextrafs.pl -f /data
```

### Ensure Open-iSCSI Enabled
1. Ensure the InitiatorName is given
```
sudo cat /etc/iscsi/initiatorname.iscsi
```
2. Ensure the status is Active
```
systemctl status iscsid
```
```
● iscsid.service - iSCSI initiator daemon (iscsid)
     Loaded: loaded (/lib/systemd/system/iscsid.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2022-06-07 14:07:37 EDT; 1min 33s ago
TriggeredBy: ● iscsid.socket
       Docs: man:iscsid(8)
    Process: 1998 ExecStartPre=/lib/open-iscsi/startup-checks.sh (code=exited, status=0/SUCCESS)
    Process: 2005 ExecStart=/sbin/iscsid (code=exited, status=0/SUCCESS)
   Main PID: 2007 (iscsid)
      Tasks: 2 (limit: 462706)
     Memory: 4.1M
     CGroup: /system.slice/iscsid.service
             ├─2006 /sbin/iscsid
             └─2007 /sbin/iscsid
```
3. Enable iSCSI (if needed)
```
sudo systemctl enable --now iscsid
```

## Installation: MicroK8s
1. Install `microk8s` and wait until it is ready
```
sudo apt update && sudo apt install -y snapd && sudo snap install microk8s --classic && sudo microk8s status --wait-ready
```
```
microk8s is running
high-availability: no
  datastore master nodes: 127.0.0.1:19001
  datastore standby nodes: none
addons:
  enabled:
    ha-cluster           # (core) Configure high availability on the current node
  disabled:
    community            # (core) The community addons repository
    dashboard            # (core) The Kubernetes dashboard
    dns                  # (core) CoreDNS
    gpu                  # (core) Automatic enablement of Nvidia CUDA
    helm                 # (core) Helm 2 - the package manager for Kubernetes
    helm3                # (core) Helm 3 - Kubernetes package manager
    host-access          # (core) Allow Pods connecting to Host services smoothly
    hostpath-storage     # (core) Storage class; allocates storage from host directory
    ingress              # (core) Ingress controller for external access
    mayastor             # (core) OpenEBS MayaStor
    metallb              # (core) Loadbalancer for your Kubernetes cluster
    metrics-server       # (core) K8s Metrics Server for API access to service metrics
    prometheus           # (core) Prometheus operator for monitoring and logging
    rbac                 # (core) Role-Based Access Control for authorisation
    registry             # (core) Private image registry exposed on localhost:32000
    storage              # (core) Alias to hostpath-storage add-on, deprecated
```

2. Edit the default configuration to use the new partition to store container data
```
sudo vi /var/snap/microk8s/current/args/containerd
```
```
--config ${SNAP_DATA}/args/containerd.toml
--root /data/var/lib/containerd
--state /data/run/containerd
--address ${SNAP_COMMON}/run/containerd.sock
```
```
sudo microk8s stop && sudo microk8s start
```

3. Disable high-availability
```
sudo microk8s disable ha-cluster --force
```

4. Enable DNS and ingress
```
bash
sudo microk8s enable dns
sudo microk8s enable ingress
sudo microk8s enable community
sudo microk8s enable istio
```

## Installation: OpenEBS
1. Install OpenEBS-cStor
```
sudo microk8s kubectl apply -f openebs-operator.yaml && watch sudo microk8s kubectl get pod -n openebs
```
```
NAME                                           READY   STATUS    RESTARTS   AGE
maya-apiserver-66d58db55f-lgq7n                1/1     Running   0          104s
openebs-admission-server-76ff697fcf-wss86      1/1     Running   0          103s
openebs-localpv-provisioner-66564d9999-t978f   1/1     Running   0          103s
openebs-ndm-operator-75ff8ddc79-fxsqr          1/1     Running   0          103s
openebs-ndm-q8d6g                              1/1     Running   0          103s
openebs-provisioner-5548f4bc77-8qjq9           1/1     Running   0          103s
openebs-snapshot-operator-776b54cd85-zqkz2     2/2     Running   0          103s
```

2. Make sure the block device is recognized, unclaimed, and active
```
sudo microk8s kubectl get bd -n openebs
```
```
NAME                                           NODENAME                                                  SIZE            CLAIMSTATE   STATUS   AGE
blockdevice-1996ceb7c2142948c5738883650fd29c   node-0.khchow-127506.c4420-6422-pg0.clemson.cloudlab.us   1000204886016   Unclaimed    Active   60s
```

3. Create a YAML file: `vi spc.yaml` with the correct node name and block device name
```
apiVersion: openebs.io/v1alpha1
kind: StoragePoolClaim
metadata:
  name: cstor-disk-pool
  annotations:
    cas.openebs.io/config: |
      - name: PoolResourceRequests
        value: |-
            memory: 2Gi
      - name: PoolResourceLimits
        value: |-
            memory: 4Gi
spec:
  name: cstor-disk-pool
  type: disk
  poolSpec:
    poolType: striped
  blockDevices:
    blockDeviceList:
    - TODO
```

4. Apply the YAML file
```
sudo microk8s kubectl apply -f spc.yaml && watch sudo microk8s kubectl -n openebs get pods
```

5. Make sure the disk pool is healty: 
```
sudo microk8s kubectl get csp
```
```
NAME                   ALLOCATED   FREE   CAPACITY   STATUS    READONLY   TYPE      AGE
cstor-disk-pool-zl4x   660K        928G   928G       Healthy   false      striped   2m8s
```

6. Create the storage class
```
sudo microk8s kubectl apply -f sc.yaml && watch sudo microk8s kubectl -n openebs get sc
```

## Installation: Telemetry Tools

1. Apply kube-prometheus and kiali stack YAMLs
```
sudo microk8s kubectl create namespace monitoring
sudo microk8s kubectl apply --server-side -f monitoring/setup
sudo microk8s kubectl apply -f monitoring/ && watch sudo microk8s kubectl get all -n monitoring
sudo microk8s kubectl apply -f monitoring/openebs-addons
```

2. Apply jaeger-elasticsearch stack YAMLs
```
sudo microk8s kubectl apply -f tracing/00-elasticsearch-pvc.yaml
sudo microk8s kubectl apply -f tracing/01-elasticsearch.yaml
sudo microk8s kubectl apply -f tracing/02-cert-manager.yaml
sudo microk8s kubectl apply -f tracing/03-jaeger-operator.yaml
sudo microk8s kubectl apply -f tracing/04-jaeger.yaml
```

3. Change the type of `ClusterIP` to `NodePort`
```
sudo microk8s kubectl -n monitoring edit svc prometheus-k8s
sudo microk8s kubectl -n monitoring edit svc grafana
sudo microk8s kubectl -n monitoring edit svc jaeger-elasticsearch-query
sudo microk8s kubectl -n istio-system edit svc kiali
```

4. Get the port numbers
```
sudo microk8s kubectl get services --all-namespaces
```

## Installation: Social Network
1. Create namespace and PVCs
```
sudo microk8s kubectl apply -f social-network-deploy/k8s-yaml/init/ && watch sudo microk8s kubectl get pods -n openebs
```

2. Apply social-network stack YAMLs
```
sudo microk8s kubectl apply -f social-network-deploy/k8s-yaml/ && watch sudo microk8s kubectl get pods -n social-network
```

3. Configure gateway for Istio
```
export INGRESS_PORT=$(sudo microk8s kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].nodePort}')
export SECURE_INGRESS_PORT=$(sudo microk8s kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')
export TCP_INGRESS_PORT=$(sudo microk8s kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="tcp")].nodePort}')
export INGRESS_HOST=$(sudo microk8s kubectl get po -l istio=ingressgateway -n istio-system -o jsonpath='{.items[0].status.hostIP}')
sudo microk8s kubectl apply -f gateway.yaml
```

4. **Important!** Create an index on `filename` on `media-mongodb`
```
sudo microk8s kubectl exec -it media-mongodb-c696bd674-xl9qr -n social-network -- bash  
mongo
use media
db.media.createIndex({"filename": 1})
```

4. **Important!** Create an index on `username` on `user-mongodb`
```
sudo microk8s kubectl exec -it media-mongodb-c696bd674-xl9qr -n social-network -- bash  
mongo
use user
db.user.createIndex({"username": 1})
```

# Miscellaneous
## Troubleshooting
1. Node health
```
sudo microk8s kubectl describe no
```

## Known Issues
- [ ] The hotel reservation system does not use OpenEBS. Restarting the pods can result in data loss.
