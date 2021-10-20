# ld_server
Linkage disequilibrium server

This repo contains LD server code, associated k8s deployment files and wdl workflows. We're running this with k8s at api.finngen.fi.

The server code is in [ld_server.py](ld_server.py). LD is calculated with a [modified Tomahawk](https://github.com/FINNGEN/tomahawk). We're using the gunicorn server with [run.py](run.py).

Docker image in [GCR](https://console.cloud.google.com/gcr/images/finngen-refinery-dev/GLOBAL/ld_server)

## API usage

The only endpoint currently is `/api/ld` used to get LD between a query variant and all variants within a base pair window.

`http://api.finngen.fi/api/ld?variant=6:44693011:A:G&window=1000000&panel=sisu3&r2_thresh=0.9`

`variant`, `window` and `panel` are required query parameters. `r2_thresh` is optional. Variant needs to be chr:pos:ref:alt. Can have chr prefix. X can be X or 23. Window size is limited in [config.py](config.py). Currently sisu3 and sisu4 imputation panels are supported (contain the same variants as imputed FinnGen data: sisu3 until data freeze 7 and sisu4 from data freeze 8 onwards).

## Creating a Docker image

```
docker build -t eu.gcr.io/finngen-refinery-dev/ld_server:VERSION -f deploy/Dockerfile .
docker push eu.gcr.io/finngen-refinery-dev/ld_server:VERSION
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

## WDL for converting imputation panel VCF to TWK

Tomahawk uses a .twk format for storing genotypes. Use [wdl/tomahawk_import.wdl](wdl/tomahawk_import.wdl) and [wdl/tomahawk_import.json](wdl/tomahawk_import.json) to convert VCF to TWK.

## Changelog

0.1.5 initial release  
0.1.6 fixed tabix threading issue (0932a43)  
0.2.0 support for both sisu3 and sisu4 (7f2c886)
