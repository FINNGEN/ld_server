# ld_server
Linkage disequilibrium server

This repo contains LD server code, associated k8s deployment files and wdl workflows. We're running this in `finngen-ld` IP `35.186.212.248` with k8s.

API usage:

The only endpoint currently is `/api/ld` used to get LD between a query variant and all variants within a base pair window.

`http://35.186.212.248/api/ld?variant=chrX:130355577:A:C&window=1000000&panel=sisu3`

variant, window and panel are required. Variant needs to be chr:pos:ref:alt. Can have chr prefix. X can be X or 23. Window size is limited in [config.py](config.py). Currently the sisu3 ~4000 Finns WGS imputation panel is supported (contains the same variants as imputed FinnGen data).

The server code is in [ld_server.py](ld_server.py). LD is calculated with a [modified Tomahawk](https://github.com/FINNGEN/tomahawk). We're using the gunicorn server [run.py](run.py).

## Creating a Docker image

```
docker build -t gcr.io/finngen-refinery-dev/ld_server:0.1.VERSION -f deploy/Dockerfile .
docker push gcr.io/finngen-refinery-dev/ld_server:0.1.VERSION
```

## Modifying the existing Kubernetes deployment

kubectl is required. We're currently using a cluster called `ld` in `finngen-refinery-dev`.

To modify the existing deployment, e.g. after updating the Docker image in [deploy/ld_server_deployment.yaml](deploy/ld_server_deployment.yaml) or changing the disk in [deploy/ld_server_pv.yaml](deploy/ld_server_pv.yaml):

```
gcloud config set project finngen-refinery-dev
gcloud container clusters get-credentials ld
kubectl config use-context gke_finngen-refinery-dev_europe-west1-b_ld
```

```
kubectl apply -f deploy/ld_server_deployment.yaml
kubectl delete pod ld-server-0
```

Logs:

```
kubectl get events --sort-by=.metadata.creationTimestamp
kubectl logs ld-server-0
```

## Creating a new Kubernetes cluster and deploying

Create cluster, e.g.:

```
gcloud container clusters create CLUSTER_NAME --machine-type n1-highcpu-4 --num-nodes 1 --zone europe-west1-b --subnetwork cromwell-subnet --project finngen-refinery-dev
```

Check the k8s context:

```
kubectl config get-contexts
```

Change the context if necessary:

```
kubectl config use-context gke_finngen-refinery-dev_europe-west1-b_CLUSTER_NAME
```

Deploy:

```
kubectl create --save-config -f deploy/ld_server_ingress.yaml
kubectl create --save-config -f deploy/ld_server_pv.yaml
kubectl create --save-config -f deploy/ld_server_deployment.yaml
```

## WDL for converting VCF to TWK

Tomahawk uses a .twk format for storing genotypes. Use [wdl/tomahawk_import.wdl](wdl/tomahawk_import.wdl) and [wdl/tomahawk_import.json](wdl/tomahawk_import.json) to convert VCF to TWK.
