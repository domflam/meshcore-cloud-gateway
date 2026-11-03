# Météo du Club — PWA Android

Application web responsive installable depuis une icône, issue du prototype
`feature/weather-dashboard-prototype`. Service autonome de lecture seule :
aucune modification du firmware ni de l’API d’ingestion en fonctionnement.

## Fonctionnement

- BME280 : température, humidité et pression ; batterie en volts, sans pourcentage inventé.
- Vent : zéro conservé, badge « SIMULÉ » uniquement si le booléen est vrai.
- Date du relevé en heure locale ; avertissement au-delà de cinq minutes.
- Historique de température disponible sur les dernières 24 h, jusqu’à 300 points.
- Actualisation toutes les 90 s quand l’application est visible ; bouton manuel.
- Valeurs manquantes affichées « — » ; elles ne deviennent jamais zéro.
- Erreur de lecture explicitée ; les valeurs encore affichées gardent leur date.
- Aucun token d’ingestion ou accès BigQuery dans le navigateur.

## Aperçu local, sans accès GCP

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DASHBOARD_DEMO=1 python app.py
```

Ouvrir http://127.0.0.1:8081. Le bandeau précise que les deux relevés du
3 novembre 2026 sont des captures de validation. Ils ne sont pas rafraîchis
artificiellement et ne représentent pas le direct. Ne jamais activer
DASHBOARD_DEMO sur le service qui doit présenter les vraies mesures.

```sh
python -m unittest discover -s tests -v
```

Les tests couvrent accès fermé par défaut, origine du login, cookies HTTPS,
limitation des tentatives, contrat des exemples,
requête bornée par nœud et temps, déduplication, cache et assets d’installation.
Le résultat BigQuery est simulé ; la connexion au vrai service reste à valider.

## Raccordement GCP à valider avant déploiement

Déployer un **nouveau** service `meshcore-weather-dashboard`, dans le projet
`meshcore-cloud-gateway`, région `europe-west1`. Ne pas remplacer
`meshcore-ingestion`. Aucune commande GCP n’a été exécutée pour cette PWA.

1. Compte de service dédié `weather-dashboard`, avec BigQuery Job User pour
   lancer les requêtes et BigQuery Data Viewer sur la table `meshcore.telemetry`
   (ou le dataset si l’administration ne permet pas la portée table).
   Aucun droit d’écriture et aucun accès au secret d’ingestion.
2. Créer deux nouveaux secrets : `weather-dashboard-password` (au moins
   16 caractères, mot de passe utilisateur distinct du token d’ingestion) et
   `weather-dashboard-session` (au moins 32 caractères aléatoires).
   Donner au compte de service Secret Accessor sur ces deux secrets uniquement.
3. Configurer `BQ_TABLE=meshcore-cloud-gateway.meshcore.telemetry`,
   `WEATHER_NODE_ID=RAK4631-LAB`, `DASHBOARD_PASSWORD` et `SESSION_SECRET`
   depuis Secret Manager. Ne pas définir `DASHBOARD_DEMO`.
4. Construire avec le Dockerfile fourni et examiner la configuration avant
   déploiement. L’accès HTTPS doit pouvoir atteindre la page de connexion depuis
   le téléphone ; le serveur protège la lecture par une session authentifiée.
   Ne pas réutiliser le compte de service d’ingestion. Définir au départ une
   seule instance maximale pour conserver un cache unique et borner les coûts.
5. Valider login, `/api/weather` inaccessible sans session, correspondance des
   relevés avec BigQuery, état vide, erreurs de lecture et logout.
6. L’installation Android doit être validée sur le vrai téléphone, en HTTPS.

L’authentification par mot de passe et le frein aux tentatives sont un choix
LAB. Le frein est en mémoire, propre à une instance et perdu au redémarrage.
Pour un accès public ou partagé, prévoir une identité individuelle/IAP ou un
contrôle en amont avec limitation durable avant publication plus large.
Une session dure au plus 24 h d’inactivité. Un changement de SESSION_SECRET
invalide les cookies existants. Aucun mot de passe n’est écrit dans Git.
Le proxy HTTPS Cloud Run est pris en compte pour valider l’origine des logins.

## Coût de lecture

Une lecture utilise le cache serveur pendant 60 s. La requête filtre le nœud,
les 24 dernières heures (filtre de partition), déduplique par event_id, limite
le résultat à 300 points et le volume facturable à 100 Mo par requête.
Le cache est propre à chaque instance. Aucun rafraîchissement en arrière-plan
lorsque l’onglet est masqué. Ces bornes ne constituent pas un budget GCP.

## Icône sur l’écran d’accueil

Le manifeste contient le nom, l’icône 192/512 et une variante maskable,
l’ouverture autonome et les couleurs. Voir les exigences d’installation :
https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Making_PWAs_installable

Après déploiement HTTPS validé : ouvrir l’URL dans Chrome Android, se connecter,
puis menu ⋮ → **Installer l’application** ou **Ajouter à l’écran d’accueil**.
Le bouton de la page apparaît seulement si le navigateur expose cette option.
Les mesures se mettent à jour à l’ouverture ; ce n’est pas un widget Android.

Le service worker conserve seulement l’interface et les icônes, jamais les
réponses API ou les mesures privées. Sans réseau, l’interface peut s’ouvrir mais
ne prétend pas disposer de nouveaux relevés ; un rechargement complet hors ligne
ne dispose pas des anciennes valeurs. L’installation réelle sur Android et
la connexion GCP ne sont pas validées par le seul aperçu local.

## Scripts Cloud Shell (exécuter dans cet ordre)

Après validation de la mise en ligne :

```sh
bash prototype/weather-dashboard/scripts/prepare-gcp.sh
bash prototype/weather-dashboard/scripts/build-image.sh
bash prototype/weather-dashboard/scripts/deploy.sh
```

Le premier script ajoute les droits au compte dédié et génère les nouveaux secrets
sans les afficher. Les secrets déjà présents ne sont pas écrasés. Il ne modifie
pas le service d’ingestion. Le deuxième construit une image distincte. Le dernier
crée le service HTTPS avec login applicatif ; il rend la page d’accueil accessible
sur Internet mais pas les relevés sans session. Aucun mode démonstration n’est activé.
Ne lancer le dernier script qu’après succès de la préparation et de la compilation.

Récupérer le mot de passe pour son usage personnel, dans Cloud Shell uniquement :

```sh
gcloud secrets versions access latest --secret=weather-dashboard-password --project=meshcore-cloud-gateway
```

Ne jamais envoyer le résultat dans une discussion ou un ticket. Le secret de
session n’a pas besoin d’être consulté. Les scripts sont vérifiés syntaxiquement ;
ils doivent encore être exécutés et validés sur le projet.

Références GCP :
- https://docs.cloud.google.com/bigquery/docs/control-access-to-resources-iam
- https://docs.cloud.google.com/run/docs/configuring/services/secrets
- https://docs.cloud.google.com/sdk/gcloud/reference/run/deploy
