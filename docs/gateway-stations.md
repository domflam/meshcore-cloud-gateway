# Deux stations configurables sur la passerelle

Cette évolution concerne uniquement le firmware Heltec. L'API GCP, BigQuery et
le contrat JSON restent inchangés : chaque mesure utilise le `node_id` de la
station qui vient de répondre. La clé publique est conservée localement, elle
n'est pas ajoutée à la table de mesures.

## Mise à jour et première ouverture

1. Compiler la version Wi-Fi LAB contre MeshCore
   `81dbae592ffad40b4212bc0b37e82b38da08f4bc`, avec les scripts d'injection du
   dépôt, puis vérifier la compilation avant de flasher. Aucune procédure ne
   doit effacer la mémoire NVS, les contacts ou l'identité de la passerelle.
2. Utiliser l'artefact correspondant à la station actuellement interrogée. Sans
   configuration de stations enregistrée, l'emplacement 1 reprend la clé,
   l'identifiant et le profil choisis lors de la compilation ; le second est
   désactivé. La compilation RAK proposée utilise le profil de vent réel.
3. Ouvrir le portail d'administration habituel. Dans le firmware Companion,
   `cloud setup` se tape dans **CLI Rescue**, pas dans le flux normal de logs.
   Après RESET, faire un appui long sur le bouton utilisateur pendant les
   huit premières secondes. Attendre `========= CLI Rescue =========`, puis
   envoyer `cloud setup` avec une fin de ligne CR ou CR+LF, à 115200 bauds.
4. Se connecter à `MeshCore-Gateway-Setup`, ouvrir `http://192.168.4.1/`,
   puis **Stations météo (2 emplacements)**, ou directement
   `http://192.168.4.1/stations`. Le portail reste ouvert dix minutes.

Le formulaire Stations ne lit ni ne modifie les identifiants Wi-Fi, le token,
le certificat CA, l'endpoint GCP ou l'intervalle de collecte déjà enregistrés.
La page de configuration GCP et son intervalle de 1 à 1440 minutes restent
séparés ; un champ token ou CA vide y conserve la valeur existante.

## Champs par station

- **Activer** : une station inactive n'est jamais interrogée.
- **Nom affiché** : libellé local, jusqu'à 48 octets UTF-8. Non transmis à GCP.
- **Identifiant stable (node_id)** : 1 à 64 lettres ASCII, chiffres, `_` ou `-`.
  Garder `RAK4631-LAB` pour la station existante et utiliser par exemple
  `RAK4631-CLUB` pour celle du club. La base sait déjà distinguer ces valeurs.
  Changer cet identifiant commence une série différente dans les données.
- **Clé publique** : 64 caractères hexadécimaux (32 octets), copiés depuis
  MeshCore. Ce n'est pas une clé privée. Les clés vides d'une station activée,
  entièrement nulles ou entièrement `ff` sont refusées.
- **Préréglage** : remplit les canaux sans les figer. GAT562 historique,
  RAK4631 vent réel, ou RAK4631 vent simulé. Les champs visibles font foi.
- **Canaux** : tension, température, humidité, pression et vent ; `-1` désactive
  une mesure. Les valeurs peuvent différer entre stations. Le vent correspond
  à une entrée analogique CayenneLPP déjà exprimée en m/s, sans calibration
  ajoutée par la passerelle.
- **Vent simulé** : à cocher uniquement pour le firmware qui émet un zéro
  virtuel. Un zéro mesuré par un véritable anémomètre reste du vent réel.
- **Fin de trame** : tolérance explicite de 0 à 4 octets nuls ; 1 pour la capture
  RAK validée et 4 pour le GAT562 historique.

Les doublons de clé et de `node_id` sont refusés, même si un emplacement est
inactif. Il est possible de désactiver les deux stations. Un emplacement
entièrement vide doit rester désactivé.

## Enregistrer puis redémarrer

La validation porte sur les deux emplacements avant toute écriture. Ils sont
sauvegardés ensemble dans un enregistrement NVS versionné (`gateway-nodes`),
avec contrôle d'intégrité. La sélection active reste stable jusqu'au
redémarrage : aucun changement de clé ou d'identifiant au milieu d'une réponse.
La configuration enregistrée est réaffichée par le formulaire après sauvegarde.

Au démarrage, une configuration illisible désactive l'interrogation et signale
l'erreur ; elle ne remplace pas silencieusement les stations par une autre
identité. L'opérateur peut la corriger depuis le même formulaire.

## Ajouter la station du club

1. Depuis l'application connectée à **la passerelle Heltec**, ajouter le RAK du
   club aux contacts MeshCore et vérifier une demande manuelle de télémétrie.
   Une clé dans le formulaire ne crée pas le contact ni une route radio.
2. Dans l'emplacement 2, saisir le nom, `RAK4631-CLUB`, sa vraie clé publique,
   le profil et les canaux vérifiés sur ce RAK. Activer, enregistrer, redémarrer.
3. Vérifier les lignes `[STATIONS]` au démarrage. Attendre les lignes
   `[GATEWAY] TX RAK4631-LAB`, `RX RAK4631-LAB`, puis `TX RAK4631-CLUB` et `RX`.
4. Vérifier les accusés `[CLOUD] accepted event=...`. Dans BigQuery, comparer
   les mesures et `node_id` des deux stations avec un filtre de partition sur
   `observed_at`. Ne pas modifier l'API ni le schéma pour ce test.
5. Éteindre la première station : après le timeout (30 s), la seconde doit
   être interrogée. Faire aussi un essai avec un contact manquant : il est
   ignoré pour ce cycle et l'autre station continue.
6. Redémarrer la passerelle : les deux emplacements doivent être conservés.
   Tester enfin la désactivation d'un emplacement et le refus d'un doublon.

L'intervalle commun s'applique entre deux cycles complets ; les stations sont
interrogées successivement, avec une seule requête autonome en attente. Une
requête de l'application reste prioritaire. Un contact absent ou un envoi
immédiatement refusé passe au prochain emplacement et sera réessayé au cycle
suivant. Les réponses sont associées au couple clé publique + tag attendu ; une
réponse d'une autre station ou hors délai n'est pas attribuée à la station
suivante.

Les identifiants d'événement sont créés à la réception, indépendamment de la
longueur de `node_id`, puis conservés lors des reprises HTTPS. Les limites
existantes restent celles du firmware : file de 16 lectures en RAM, perdue au
redémarrage ; déduplication BigQuery au mieux ; nécessité d'une heure correcte
et d'un CA valide pour HTTPS. Aucun flash ni déploiement n'est automatique.

## Vérifications reproductibles

```sh
python3 -m unittest discover -s tests -v
```

Ces tests exécutent le code C++ réel de validation et de sérialisation, les
handlers HTTP avec un stockage NVS simulé, l'application du patch et
l'ordonnanceur : restauration après reboot, clé/id en doublon, canaux invalides,
écriture refusée, données corrompues, station absente, deux stations inactives,
timeout, priorité Companion et retour du compteur millis à zéro.

La compilation ESP32-S3 complète avec les scripts sur la révision upstream
figée complète ces tests ; elle ne remplace pas l'essai radio sur le matériel.
