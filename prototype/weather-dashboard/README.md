# Météo CASLF — consultation publique

PWA de lecture seule, séparée de `meshcore-ingestion`. L’accueil et
`/api/weather` sont publics, sans mot de passe, session ou cookie de connexion.
Le compte GCP dédié reste limité à la lecture de la table météo. Le token
d’ingestion n’est jamais transmis au navigateur. Aucune route d’écriture.

## Thèmes et intégration WebView

- `https://meshcore-weather-dashboard-4iuwvwwbyq-ew.a.run.app/?theme=light`
- `https://meshcore-weather-dashboard-4iuwvwwbyq-ew.a.run.app/?theme=dark`

Priorité : paramètre URL valide, puis choix enregistré dans le navigateur,
puis préférence claire/sombre du système. Une valeur inconnue est ignorée.
Le bouton « Mode clair » / « Mode sombre » en bas de page inverse le thème,
mémorise le choix si le stockage est disponible et actualise l’URL sans
recharger les données. Le thème URL n’écrase pas le choix local tant que
l’utilisateur n’actionne pas le bouton. Les changements du système sont suivis
si aucun choix explicite n’existe. Les thèmes s’appliquent aussi aux courbes.

Pour le développeur de l’application de réservation : ouvrir l’URL HTTPS dans
une **WebView avec JavaScript activé**, en choisissant `theme=light` ou
`theme=dark` selon le thème de l’application hôte. Pour un changement de thème
hôte pendant l’affichage, recharger la WebView avec le nouveau paramètre.
Aucun en-tête d’authentification, cookie ou secret n’est nécessaire.
Le stockage local est facultatif ; le paramètre URL fonctionne même si celui-ci
est bloqué. La page ne dépend pas de l’installation PWA pour fonctionner.
Une WebView native est prise en charge ; l’intégration par iframe dans un autre
site reste bloquée par `frame-ancestors 'none'`.

## Relevés

Température, humidité, pression, vent réel/simulé et batterie en volts.
Quatre courbes sur 24 h, jusqu’à 300 points. Les valeurs absentes restent « — ».
Le badge SIMULÉ et les pointillés apparaissent uniquement pour `true` ; un zéro
réel reste réel. Date locale et avertissement après 30 minutes par défaut
(`WEATHER_STALE_AFTER_MINUTES`, 1..1440). Actualisation toutes les 90 secondes
quand la page est visible, et bouton manuel.

Le cache serveur dure 60 secondes par instance. Les requêtes filtrent le nœud
et les 24 dernières heures, dédupliquent par event_id et limitent le volume
facturable à 100 Mo par requête. Le déploiement conserve une instance maximale.
Le service worker conserve seulement l’interface, jamais les réponses API.
Le cache d’interface v3 remplace l’ancienne version après activation du worker ;
fermer puis rouvrir une ancienne installation si nécessaire.

## Aperçu et tests

Depuis ce dossier, installer requirements.txt dans un environnement Python.
`DASHBOARD_DEMO=1 python app.py` ouvre un aperçu sur http://127.0.0.1:8081.
Les deux relevés datés du 3 novembre sont explicitement marqués démonstration.
Ne pas activer ce mode sur le service réel.

```sh
python -m unittest discover -s tests -v
node tests/chart-model.test.cjs
node tests/theme.test.cjs
```

Tests : lecture sans session ni secrets, absence de routes login/écriture,
erreurs nettoyées, requête bornée/cache, données manquantes, assets PWA,
priorité des thèmes, bouton, stockage bloqué et préservation des paramètres URL.
Les résultats BigQuery sont simulés dans les tests.

## Mise à jour du service existant

Depuis la racine du dépôt, après validation de la nouvelle version :

```sh
bash prototype/weather-dashboard/scripts/build-image.sh
bash prototype/weather-dashboard/scripts/deploy.sh
```

Le déploiement ne concerne que `meshcore-weather-dashboard`. Il retire les
références aux secrets DASHBOARD_PASSWORD et SESSION_SECRET du service, sans
supprimer les secrets historiques ni modifier le service d’ingestion.
Il conserve le compte dédié et l’accès public Cloud Run déjà existant.
Aucun nouveau secret n’est requis. Pour une première installation seulement,
`prepare-gcp.sh` prépare le compte et les droits BigQuery de lecture.

Après déploiement : ouvrir une fenêtre privée sans connexion, vérifier les
relevés et les deux URL de thème, le bouton et la WebView Android réelle.
L’installation PWA reste accessible depuis Chrome → Ajouter à l’écran d’accueil.
