mkdir logs
mkdir plugins
chmod 755 dags logs plugins
echo "AIRFLOW_UID=$(id -u)\nAIRFLOW_GID=0" > .env
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/2.2.0/docker-compose.yaml'
chmod 755 docker-compose.yaml
docker-compose up airflow-init
