# HAClientControl für Home Assistant

Home-Assistant-Integration, die einen Windows-PC mit dem Dienst HAClientControl über MQTT steuert:
ein Button „Anmelden / Entsperren“, ein Button „PC sperren“ (ab 0.7.0) und ein Sensor „Letztes Ergebnis“.
Die am PC eingerichteten Anwendungen („<Name> starten“) sind in dieser Integration **nicht** enthalten; sie gibt es
nur über die MQTT-Discovery des Dienstes. Sie ist die Alternative zur
MQTT-Discovery des Dienstes.

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

Beide Entitäten sind nur verfügbar, solange `<Basis>/availability` den Wert `online` hat.

## Broker-ACL

Wie im Hauptprojekt: Der Benutzer `ha_logon_trigger` braucht

```
user ha_logon_trigger
topic write <Basis>/logon/request
topic read <Basis>/logon/result
topic read <Basis>/availability
```

## Sicherheit

Wer den Button drücken kann, kann den Desktop des PCs öffnen. Den Zugriff auf die Entität und die ACL des
Brokers entsprechend einschränken.
