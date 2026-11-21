# HAClientControl für Home Assistant

Home-Assistant-Integration, die einen Windows-PC mit dem Dienst HAClientControl über MQTT steuert:
ein Button „Anmelden / Entsperren“, ein Button „PC sperren“ (ab 0.7.0) und ein Sensor „Letztes Ergebnis“.
Ab 0.7.3 kommt je am PC freigegebener Anwendung ein Button „<Name> starten“ dazu (siehe unten, „App-Buttons“).
Die Integration ist die Alternative zur MQTT-Discovery von Home Assistant für denselben PC.

**Wichtig:** Am selben PC entweder diese Integration **oder** die Dienst-Option „MQTT-Discovery“ nutzen, nicht
beides, sonst entstehen doppelte Buttons.

## Installation über HACS

1. HACS → Menü → *Benutzerdefinierte Repositories*.
2. Repository `https://github.com/itfhunter/HAClientControl`, Typ *Integration*, hinzufügen.
3. „HAClientControl“ installieren und Home Assistant neu starten.

Der Windows-Client (MSI) wird separat bereitgestellt. Die MQTT-Integration von Home Assistant muss eingerichtet sein.

## Einrichtung

*Einstellungen → Geräte & Dienste → Integration hinzufügen → HAClientControl.*

- **Topic-Basis:** wie `mqtt_topic_base` im Dienst (Standard `windows/buero`). Nicht erlaubt: leer, `+`, `#`,
  führender oder abschließender `/`, Steuerzeichen. Jede Basis kann nur einmal eingerichtet werden.
- **Gerätename:** Standard „Windows-PC“.

## Entitäten

- **Button „Anmelden / Entsperren“:** sendet beim Drücken einen Auftrag auf `<Basis>/logon/request`
  (QoS 1, nicht retained). Sonst wird nie etwas veröffentlicht, auch nicht bei Start, Reload oder Reconnect.
- **Sensor „Letztes Ergebnis“:** zuletzt vom PC gemeldeter Status (`accepted`, `logged_in`, `unlocked`, …).
  Attribute: `request_id`, `finished_at`, `action`, `app_id`, `eigener_auftrag` (Ergebnis gehört zum zuletzt von diesem Button
  gesendeten Auftrag).

- **App-Buttons „<Name> starten“ (ab 0.7.3):** je freigegebener Anwendung ein Button, der einen `launch_app`-Auftrag
  mit der `app_id` sendet (gleicher Kanal, QoS 1, nicht retained, nur beim Drücken).

Alle Entitäten sind nur verfügbar, solange `<Basis>/availability` den Wert `online` hat.

## App-Buttons

Die Integration liest die App-Liste aus der retained MQTT-Discovery des Dienstes
(`homeassistant/device/<Node>/config`, `<Node>` = `hacc_` + Topic-Basis, jedes Zeichen außer `A-Za-z0-9_-` wird `_`;
für `windows/buero` also `hacc_windows_buero`). Voraussetzung: am PC ist **„In Home Assistant anzeigen
(MQTT-Discovery)“** aktiv. Pfade und Argumente stehen dort nie, nur Name und `app_id`.

- Neue Anwendung: Button erscheint ohne Neustart. Umbenennung: gleiche Entität (unique_id `<Basis>_app_<app_id>`),
  neuer Name. Entfernte Anwendung (Tombstone oder nicht mehr in der Liste): Entität und Registry-Eintrag werden gelöscht.
- Eine leere oder ungültige Discovery-Nachricht wird ignoriert; wer die Dienst-Discovery abschaltet, behält die
  bisherigen App-Buttons (sie bleiben bis zur nächsten gültigen Liste bestehen).
- Beim Start wird die retained Nachricht gelesen; dabei wird nie ein Auftrag gesendet.
- Hat Home Assistant selbst die MQTT-Discovery aktiv, entstehen die Buttons doppelt (einmal durch HA-MQTT, einmal
  durch diese Integration). Dann entweder die Dienst-Discovery-Nachricht nicht von HA verarbeiten lassen
  (MQTT-Option „Discovery aktivieren“ aus) oder die Integration nicht nutzen.

## Broker-ACL

Wie im Hauptprojekt: Der Benutzer `ha_logon_trigger` braucht

```
user ha_logon_trigger
topic write <Basis>/logon/request
topic read <Basis>/logon/result
topic read <Basis>/availability
# nur für die App-Buttons (ab 0.7.3), <Node> siehe oben:
topic read homeassistant/device/<Node>/config
```

## Sicherheit

Wer den Button drücken kann, kann den Desktop des PCs öffnen. Den Zugriff auf die Entität und die ACL des
Brokers entsprechend einschränken.
