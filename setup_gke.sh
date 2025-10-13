# Install nginx ingress controller
kubectl create namespace ingress-nginx
kubens ingress-nginx

helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install nginx-ingress ingress-nginx/ingress-nginx

# Install rabbitmq
kubectl create namespace rabbitmq
kubens rabbitmq
helm upgrade --install my-prod-rabbitmq ./my-rabbitmq

# Test access rabbitmq management UI
# kubectl port-forward svc/my-prod-rabbitmq 15672:15672

# Setup database
source export_values.sh

# Change password in google cloud sql
# Create database, tables

# Install api gateway
kubectl create namespace service-dev
kubens service-dev
helm upgrade --install api-gateway ./api_gateway

