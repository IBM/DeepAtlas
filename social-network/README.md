# Microservice-based Social Network
![Microservices](assets/social-network.png)
This directory is a microservice-based social network modified based on the [DeathStarBench](https://github.com/delimitrou/DeathStarBench). For more details, you can refer to our paper at EuroSys'24:
> Ka-Ho Chow, Umesh Deshpande, Veera Deenadhayalan, Sangeetha Seshadri, and Ling Liu, "Atlas: Hybrid Cloud Migration Advisor for Interactive Microservices," ACM European Conference on Computer Systems (EuroSys), Athens, Greece, Apr. 22-25, 2024.

It includes the following two components:   
* `./social-network-deploy/`: the yaml files for deploying the application on the cloud
* `./social-network-source/`: the source code of the social network

## Installation: MicroK8s
1. Install `microk8s` and wait until it is ready
```
sudo apt update && sudo apt install -y snapd && sudo snap install microk8s --classic && sudo microk8s status --wait-ready
```

2. Enable all necessary packages
```
sudo microk8s enable dns
sudo microk8s enable ingress
sudo microk8s enable community
sudo microk8s enable istio
```

## Installation: OpenEBS
1. Install OpenEBS
```
sudo microk8s kubectl apply -f openebs-operator.yaml && watch sudo microk8s kubectl get pod -n openebs
```

2. Make sure the block device is recognized, unclaimed, and active
```
sudo microk8s kubectl get bd -n openebs
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

5. Make sure the disk pool is healthy: 
```
sudo microk8s kubectl get csp
```

6. Create the storage class
```
sudo microk8s kubectl apply -f sc.yaml && watch sudo microk8s kubectl -n openebs get sc
```

## Installation: Social Network
1. Create namespace and PVCs
```
sudo microk8s kubectl apply -f k8s-yaml/init/ && watch sudo microk8s kubectl get pods -n openebs
```

2. Apply social-network stack YAMLs
```
sudo microk8s kubectl apply -f k8s-yaml/ && watch sudo microk8s kubectl get pods -n social-network
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

3. Configure gateway for Istio
```
export INGRESS_PORT=$(sudo microk8s kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="http2")].nodePort}')
export SECURE_INGRESS_PORT=$(sudo microk8s kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="https")].nodePort}')
export TCP_INGRESS_PORT=$(sudo microk8s kubectl -n istio-system get service istio-ingressgateway -o jsonpath='{.spec.ports[?(@.name=="tcp")].nodePort}')
export INGRESS_HOST=$(sudo microk8s kubectl get po -l istio=ingressgateway -n istio-system -o jsonpath='{.items[0].status.hostIP}')
sudo microk8s kubectl apply -f gateway.yaml
```