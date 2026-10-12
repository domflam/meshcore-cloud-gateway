# meshcore-cloud-gateway

Passerelle météo pour **Heltec V3**, basée sur MeshCore Companion BLE.
Objectif : interroger les repeaters, publier vers Cloud Run, puis alimenter
le stockage et l'application météo.

**POC-01 : collecte radio autonome après configuration et mise à l'heure.**
Ce jalon conserve l'application mobile et produit des mesures LPP brutes dans
la console USB. Wi-Fi, HTTPS et Cloud Run sont les jalons suivants.
La coexistence sur matériel doit encore être validée.

## Base officielle

- Source : [meshcore-dev/MeshCore](https://github.com/meshcore-dev/MeshCore).
- Révision : `a366955cb2f67b8e6842d4f00d2b6a554dddd88a` (30 septembre 2026).
- Cible d'origine : `Heltec_v3_companion_radio_ble`.
- Nouvelle cible : `Heltec_v3_cloud_gateway_ble`.
- Documentation originale : [README.upstream.md](README.upstream.md).
- Les licences et mentions du projet d'origine sont conservées.

## Comportement

- Aucun contact configuré par défaut : aucune interrogation automatique.
- Jusqu'à huit clés publiques complètes, configurées localement.
- Une seule requête automatique en vol, sans attente bloquante.
- Délai de démarrage de 30 secondes, puis attente de la mise à l'heure par l'app.
- Cibles interrogées successivement, avec cinq secondes entre deux cibles.
- Nouvelle tournée 15 minutes après la fin de la précédente.
- Timeout estimé par MeshCore + deux secondes, plafonné à 302 secondes.
- Après un échec, passage à la cible suivante ; nouvelle tentative à la tournée
  suivante, sans retransmissions rapprochées.
- Corrélation indépendante par tag **et clé publique complète**, sans toucher
  aux états `pending_*` du Companion.
- Conservation des 16 dernières requêtes pour absorber réponses tardives et doublons.
- File RAM de huit mesures ; si pleine, la nouvelle mesure est abandonnée et
  `dropped` augmente. Cette file volatile n'est pas un stockage durable.

## Configuration et compilation

Installer PlatformIO Core (la CI utilise 6.2.0), puis copier
`examples/companion_radio/gateway/gateway.example.h` vers `gateway.local.h`
dans le même dossier. Ce fichier local est ignoré par Git.

Remplacer l'exemple par les clés **publiques** des contacts RAK et GAT,
64 caractères hexadécimaux chacune :

```cpp
#define GATEWAY_TARGET_KEYS { \
  "CLE_PUBLIQUE_COMPLETE_DU_RAK", \
  "CLE_PUBLIQUE_COMPLETE_DU_GAT" \
}
#define GATEWAY_INTERVAL_MS 900000UL
```

Ces chaînes sont des emplacements à remplacer, pas des clés valides. Un format
invalide ou un doublon augmente `invalid_targets` et est ignoré. Ne jamais utiliser
la clé privée du Companion. Sans fichier local, la cible compile avec une liste vide.

```sh
pio run -e Heltec_v3_cloud_gateway_ble
```

Le résultat est dans `.pio/build/Heltec_v3_cloud_gateway_ble/`. Les firmwares de CI
ont une liste vide : compiler avec sa configuration locale pour une collecte réelle.

## Essai sur la Heltec

1. Sauvegarder l'identité et les réglages utiles avec les moyens habituels de l'app.
   La même identité publique doit rester autorisée sur les repeaters.
2. Flasher sans effacement complet :
   `pio run -e Heltec_v3_cloud_gateway_ble -t upload`.
3. Connecter l'app BLE, vérifier les contacts, les réglages radio et la télémétrie
   manuelle de chaque repeater. Le rôle invité n'expose que la télémétrie de base ;
   cette identité doit disposer des permissions nécessaires aux capteurs météo.
4. Mettre l'horloge à jour avec le client Companion. Le firmware attend une commande
   `CMD_SET_DEVICE_TIME` acceptée pendant ce démarrage. Si l'app ne la transmet pas
   automatiquement, utiliser un client offrant la synchronisation.
5. Ouvrir `pio device monitor -e Heltec_v3_cloud_gateway_ble`. Le statut doit afficher
   `clock_ready: true`, le nombre de cibles et zéro `invalid_targets`.
6. Déconnecter le téléphone et vérifier les tournées suivantes. Reconnecter ensuite
   l'app et demander statut/télémétrie pendant une tournée automatique.

**Après chaque redémarrage, une nouvelle mise à l'heure via le client est nécessaire.**
L'ESP32 peut démarrer avec une heure ancienne, et les repeaters rejettent les tags
temporels qui n'avancent pas. L'heure restaurée à partir des contacts ne suffit pas
à autoriser le scheduler. La mise à l'heure réseau appartient au jalon Wi-Fi :
ce POC n'est pas encore autonome après coupure d'alimentation.

Les logs gateway sont des lignes JSON avec le champ `gateway`. Des logs MeshCore
peuvent apparaître sur la même console. Le POC utilise le BLE pour le protocole
Companion et l'USB pour les diagnostics texte : ne pas ajouter `ENABLE_USB_INTERFACE`
à cette cible sans séparer les deux flux.

Une mesure contient `public_key`, `tag`, `received_at` (heure de réception sur la
passerelle, pas heure de mesure) et `lpp_hex`. Le futur décodeur devra conserver le
type et le canal LPP, pour distinguer notamment température interne et température
du capteur d'environnement.

## Validation

Tests sur ordinateur avec détection d'erreurs mémoire :

```sh
c++ -std=c++11 -Wall -Wextra -Werror -fsanitize=address,undefined \
  tests/gateway/scheduler_test.cpp -o /tmp/scheduler-test
/tmp/scheduler-test
```

Ils couvrent les clés, l'horloge préalable, la corrélation, la copie des buffers,
les doublons, les réponses tardives, les timeouts, les erreurs d'envoi, la saturation
de file et le débordement de `millis()`. La CI compile aussi le Companion BLE d'origine
et la cible gateway. Les anciennes automatisations de publication restent réservées
au dépôt MeshCore officiel.

La validation matérielle doit encore couvrir les deux repeaters, la collecte sans
téléphone après mise à l'heure, les commandes mobiles pendant une collecte, l'absence
d'un repeater et le redémarrage. Relever les compteurs de pertes/timeouts et les
délais de traitement LoRa.

## Suite

1. Wi-Fi, reconnexion et SNTP, avec BLE actif.
2. HTTPS dans une tâche dédiée, alimentée par une queue bornée par copie.
3. Cloud Run : contrat d'ingestion, authentification, dédoublonnage et décodage LPP.
4. Essais BLE + LoRa + TLS : mémoire, latence de boucle, pertes et récupération réseau.

Voir [l'architecture](docs/cloud-gateway.md) pour les points d'intégration.
