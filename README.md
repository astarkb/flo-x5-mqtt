
## 📅 Contrôle de l'Horaire (Fonctionnalité Personnalisée)
Ce fork ajoute la capacité de contrôler **l'horaire de recharge Flo** directement depuis Home Assistant via MQTT.

### Fonctionnalités
* **4 Périodes de Blocage :** Configurez jusqu'à 4 plages horaires différentes pour bloquer la recharge (par exemple, durant les heures de pointe).
* **Auto-Découverte :** Crée automatiquement les contrôles dans Home Assistant (Interrupteurs, Champs de texte, Bouton Appliquer).
* **Retour Instantané :** L'interface utilisateur se met à jour et confirme l'état immédiatement (fini les valeurs "Inconnues").

### Utilisation
1. Le script annoncera automatiquement les nouveaux contrôles à Home Assistant au démarrage.
2. Cherchez un appareil nommé **"Flo X5: VOTRE_NOM_DE_BORNE"**.
3. **Début / Fin (Start/Stop) :** Entrez l'heure au format `HH:MM` (ex: `06:00`).
4. **Période Active :** Basculez l'interrupteur pour activer ou désactiver cette plage horaire.
5. **Appliquer l'Horaire (Apply) :** Cliquez sur le bouton "Press" (Appuyer) pour envoyer la programmation à la borne.

### ⚠️ Limitations Connues
1. **Appareil en doublon (Duplicate Device) :**
   Les contrôles de l'horaire apparaissent sous un **nouvel appareil** distinct dans Home Assistant (ex: `Flo X5: AAE-xxxxx`) au lieu de fusionner avec l'appareil existant qui affiche les capteurs (Voltage/Ampérage).
   * *Solution :* Vous pouvez regrouper les deux appareils dans la même "Pièce" ou "Zone" dans Home Assistant pour un affichage unifié.

2. **Synchronisation Unidirectionnelle (One-way Sync) :**
   Le système fonctionne de **Home Assistant vers la Borne**.
   * Le script ne vérifie pas (ne "poll" pas) l'état sur le serveur Flo.
   * Si vous modifiez l'horaire via l'application mobile officielle Flo, Home Assistant ne verra **pas** le changement et affichera des valeurs obsolètes.
   * *Recommandation :* Utilisez exclusivement Home Assistant pour gérer l'horaire afin de garder les données synchronisées.

3. **Tester uniquement sur VS Code:**
   * Je test sur Docker dès que possible.


# flo-x5-mqtt
Daemon to synchronize the state information of flo X5 EV chargers from the flo.ca API to HomeAssistant using MQTT.

## Pre-requisites
### Install Dependencies
To install dependencies:
`pip install requests ha_mqtt_discoverable pkce`

### Configure Environment Variables
The configuration is done through environment variables:

| Variable                | Description                                           |
|-------------------------|-------------------------------------------------------|
| `FLO_USERNAME`          | Username of the flo.ca account.                       |
| `FLO_PASSWORD`          | Password of the flo.ca account.                       |
| `FLO_STATION_NAME`      | Name of the flo X5 charging station (ex: AAE-00123).  |
| `FLO_LOG_LEVEL`         | Log level. Default: INFO                              |
| `HASS_MQTT_HOST`        | Host/IP of the MQTT server.                           |
| `HASS_MQTT_PORT`        | Port of the MQTT server.                              |
| `HASS_MQTT_USERNAME`    | Username for the MQTT server.                         |
| `HASS_MQTT_PASSWORD`    | Password for the MQTT server.                         |

### Create the `data` folder
The application uses a folder called `data` to store some state information. Create it next to `main.py` before running the application.

## Run the application
`python main.py`

## Run using Docker Compose
To use with Docker Compose, create your `docker-compose.yaml` file with the following content:
```
version: "3"
services:
  AAE-00123:
    image: glavoie84/flo-x5-mqtt:latest
    restart: unless-stopped
    environment:
      HASS_MQTT_USERNAME: ''
      HASS_MQTT_PASSWORD: ''
      HASS_MQTT_HOST: '<host or IP>'
      HASS_MQTT_PORT: '1883'
      FLO_USERNAME: ''
      FLO_PASSWORD: ''
      FLO_STATION_NAME: 'AAE-00123'
    volumes:
      - ./data:/app/data
```

## Building the Docker Image
`docker build -t flo-x5-mqtt .`