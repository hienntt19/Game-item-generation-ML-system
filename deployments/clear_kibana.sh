#!/bin/bash

echo "--- Bắt đầu dọn dẹp TOÀN BỘ tài nguyên Kibana mồ côi ---"
NAMESPACE="monitor"
RELEASE_NAME="kibana"

# 1. Xóa các Job hook đặc biệt có thể bị kẹt (pre-install, post-delete, etc.)
# Sử dụng label để tìm tất cả các job liên quan đến Kibana
echo "--- Xóa các Helm hook Jobs còn sót lại ---"
kubectl delete job -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME

# 2. Xóa tất cả các tài nguyên còn lại dựa trên label của Helm release
# Đây là cách hiệu quả và an toàn nhất để dọn dẹp
echo "--- Xóa tất cả các tài nguyên (Service, Deployment, PVC, Ingress, etc.) của Kibana ---"
kubectl delete all,pvc,ingress,secret,configmap,role,rolebinding,serviceaccount -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME

# 3. Chạy lại các lệnh xóa cụ thể của bạn để đảm bảo không còn gì sót lại
echo "--- Chạy các lệnh dọn dẹp cụ thể để chắc chắn ---"
kubectl delete secret kibana-kibana-es-token -n $NAMESPACE --ignore-not-found=true
kubectl delete configmap kibana-kibana-helm-scripts -n $NAMESPACE --ignore-not-found=true
kubectl delete serviceaccount pre-install-kibana-kibana -n $NAMESPACE --ignore-not-found=true

kubectl delete serviceaccount post-delete-kibana-kibana -n $NAMESPACE --ignore-not-found=true
kubectl delete jobs pre-install-kibana-kibana -n $NAMESPACE --ignore-not-found=true


kubectl delete roles pre-install-kibana-kibana -n $NAMESPACE --ignore-not-found=true

kubectl delete rolebinding pre-install-kibana-kibana -n $NAMESPACE --ignore-not-found=true

echo "--- Dọn dẹp hoàn tất. Môi trường đã sạch. ---"