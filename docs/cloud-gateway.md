# Architecture de la passerelle

## Chemin conservé

```text
App BLE -> checkSerialInterface -> handleCmdFrame
  commande 39 (télémétrie) ou 50 (binaire, type 0x03)
                           |
Scheduler -> sendRequest --+
                           v
BaseChatMesh -> createDatagram -> sendDirect / sendFloodScoped
                           v
Dispatcher -> RadioLibWrapper -> SX1262
```

`BaseChatMesh::sendRequest()` construit le paquet chiffré, choisit le routage,
et retourne le tag et le timeout estimé. La passerelle ne modifie ni les drivers,
ni les budgets d'émission, ni le format radio.

Côté repeater, `examples/simple_repeater/MyMesh.cpp::handleRequest()` traite
`REQ_TYPE_GET_TELEMETRY_DATA` (`0x03`). La réponse contient le tag de quatre octets
suivi du Cayenne LPP. Le contenu dépend des capteurs et des permissions dans l'ACL.
Le POC réutilise l'identité provisionnée ; il n'effectue pas de login automatique.

`Mesh::onRecvPacket()` déchiffre et vérifie le MAC, puis
`BaseChatMesh::onPeerDataRecv()` transmet à `MyMesh::onContactResponse()`.
`onContactPathRecv()` couvre aussi les réponses embarquées dans un retour de chemin.

## Modifications

| Fichier | Ajout |
| --- | --- |
| `variants/heltec_v3/platformio.ini` | Cible dérivée avec `ENABLE_CLOUD_GATEWAY` |
| `examples/companion_radio/main.cpp` | Initialisation et appel court dans la boucle Mesh |
| `examples/companion_radio/MyMesh.h` | Scheduler attaché, état de mise à l'heure |
| `examples/companion_radio/MyMesh.cpp` | Réponses gateway avant les branches historiques ; notification de mise à l'heure |
| `examples/companion_radio/gateway/TelemetryScheduler.h` | Machine à états, corrélation et file, sans Arduino |
| `examples/companion_radio/gateway/GatewayRuntime.h` | Adaptation MeshCore et diagnostic série par petits blocs |

Les réponses automatiques sont consommées avant `pending_login` et `pending_status`,
qui utilisent historiquement un préfixe de clé, pas un tag exact. Les réponses aux
demandes mobiles suivent le traitement existant. Le scheduler n'appelle jamais
`clearPendingReqs()`.

Les 16 dernières demandes restent reconnues après réponse ou timeout. Une réponse
très ancienne dont l'entrée a été évincée n'est plus attribuable au scheduler :
cette fenêtre est bornée pour limiter la RAM. Une nouvelle tournée commence
15 minutes après la dernière réponse ou le dernier timeout de la précédente.

La file actuelle est utilisée uniquement par la boucle principale. Elle n'est
**pas thread-safe** : HTTPS devra la remplacer ou la relier à une queue FreeRTOS
par copie, sans partager des pointeurs de paquets ni de `ContactInfo`.

## Jalons réseau

Conserver BLE et ajouter un Wi-Fi station. Le serveur TCP de `SerialWifiInterface`
n'est pas nécessaire pour publier ; ne pas l'activer simplement pour obtenir Wi-Fi.

La tâche réseau gérera connexion, SNTP, TLS et reprises espacées. Elle communiquera
la synchronisation à la boucle Mesh ; la politique d'horloge devra préserver les
tags croissants, y compris lors d'une correction SNTP vers le passé. Aucun appel
Mesh depuis un callback Wi-Fi.

Le certificat serveur sera validé et l'horloge synchronisée avant TLS. Le mécanisme
d'authentification Cloud Run reste à définir avec le service. Les secrets resteront
en configuration locale ignorée ou via un provisionnement dédié. Une clé API n'est
pas une identité IAM.

Contrat proposé : identité gateway, clé complète du repeater, identifiant
d'échantillon stable pour les reprises, tag, heure de réception et LPP en base64.
L'ingestion dédupliquera les reprises et conservera le brut pour les types inconnus.
L'heure de réception ne prétend pas être l'heure de mesure.

Isoler TLS réduit le risque de bloquer la radio ; cela ne prouve pas l'absence
d'impact. Mesurer mémoire libre, plus grand bloc, délais de boucle et pertes
avant/après ajout réseau, avec BLE actif et pendant les reconnexions.
