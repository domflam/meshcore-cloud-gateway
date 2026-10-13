# Météo du Club — prototype BigQuery

Mini-dashboard responsive, lecture seule : température, batterie, dernier relevé et historique 24h.
Le navigateur ne reçoit aucun accès BigQuery ; seule l'API Flask interroge BigQuery.

## Déploiement (GCP)
Depuis ce dossier, avec gcloud configuré sur le projet `meshcore-cloud-gateway` :

```bash
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com bigquery.googleapis.com
gcloud iam service-accounts create weather-dashboard --display-name="Weather dashboard read only"
SA=weather-dashboard@meshcore-cloud-gateway.iam.gserviceaccount.com
gcloud projects add-iam-policy-binding meshcore-cloud-gateway --member="serviceAccount:$SA" --role="roles/bigquery.jobUser"
# Pour un prototype : lecture au niveau du dataset meshcore, pas tout le projet.
bq add-iam-policy-binding --member="serviceAccount:$SA" --role="roles/bigquery.dataViewer" meshcore
gcloud run deploy meshcore-weather-dashboard --source . --region europe-west1 --service-account "$SA" --allow-unauthenticated --set-env-vars BQ_TABLE=meshcore-cloud-gateway.meshcore.telemetry
```

Si votre version de bq ne prend pas en charge `add-iam-policy-binding`, accordez `BigQuery Data Viewer` au compte de service sur le dataset `meshcore` dans la console GCP.

Attention : `--allow-unauthenticated` publie les relevés météo ; supprimer ce flag si l'accès doit être restreint. Ne jamais inclure le token d'ingestion dans cette application.

Hypothèses : `observed_at` est un TIMESTAMP et les colonnes `node_id`, `voltage_v`, `temperature_c` existent. Vérifier le schéma avant déploiement.
