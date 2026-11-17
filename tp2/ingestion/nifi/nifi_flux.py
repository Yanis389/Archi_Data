#!/usr/bin/env python3
"""UC-04 - Construction et pilotage des flux NiFi du TP J2 par l'API REST de NiFi 2.x (bibliothèque standard).

Le flux est aussi visible et modifiable dans l'interface https://localhost:8443/nifi : ce script sert à rendre la
construction reproductible et à produire des preuves (état des processeurs, provenance, export JSON du flux).

Identifiants : lus dans NIFI_USERNAME / NIFI_PASSWORD (jamais écrits dans le dépôt).

Sous-commandes :
  obligatoire                     flux guidé GetFile -> PutHDFS (+ failure -> LogAttribute)      [étape 8]
  enrichi                         flux enrichi : attributs, contrôles, routage, rejets, reprises [étape 12, AV-01..04]
  demarrer|arreter <groupe>       démarre / arrête tous les composants d'un Process Group
  demarrer-proc|arreter-proc <groupe> <processeur>
  etat <groupe>                   état des processeurs et des files d'attente (compteurs sur 5 min)
  config <groupe> <processeur> <propriété> <valeur>
  provenance [--nom FICHIER] [--json SORTIE]
  lignage <event_id> [--json SORTIE]
  bulletins
  exporter <groupe> <sortie.json> définition du flux (Download flow definition)
  vider <groupe>                  vide les files d'attente du groupe
  supprimer <groupe>              arrête, vide et supprime un groupe (avant reconstruction)
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = os.environ.get("NIFI_API", "https://localhost:8443/nifi-api")
# Certificat auto-signé généré par NiFi au premier démarrage : vérification désactivée UNIQUEMENT pour l'accès local.
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

P = {  # types de processeurs utilisés
    "GetFile": "org.apache.nifi.processors.standard.GetFile",
    "PutHDFS": "org.apache.nifi.processors.hadoop.PutHDFS",
    "LogAttribute": "org.apache.nifi.processors.standard.LogAttribute",
    "UpdateAttribute": "org.apache.nifi.processors.attributes.UpdateAttribute",
    "RouteOnAttribute": "org.apache.nifi.processors.standard.RouteOnAttribute",
    "PutFile": "org.apache.nifi.processors.standard.PutFile",
    "CryptographicHashContent": "org.apache.nifi.processors.standard.CryptographicHashContent",
    "RetryFlowFile": "org.apache.nifi.processors.standard.RetryFlowFile",
}
HADOOP_CONF = "/opt/hadoop/etc/hadoop/core-site.xml,/opt/hadoop/etc/hadoop/hdfs-site.xml"

G_OBLIGATOIRE = "UC04 - GetFile vers PutHDFS"
G_ENRICHI = "UC04 - Flux enrichi (attributs, controles, routage, reprises)"


class NiFi:
    def __init__(self) -> None:
        user, pwd = os.environ.get("NIFI_USERNAME"), os.environ.get("NIFI_PASSWORD")
        if not user or not pwd:
            sys.exit("NIFI_USERNAME / NIFI_PASSWORD non définis")
        data = urllib.parse.urlencode({"username": user, "password": pwd}).encode()
        req = urllib.request.Request(f"{API}/access/token", data=data, method="POST",
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
        with urllib.request.urlopen(req, context=CTX) as r:
            self.token = r.read().decode()

    def call(self, method: str, path: str, body: dict | None = None, raw: bool = False):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{API}{path}", data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, context=CTX) as r:
                txt = r.read().decode()
        except urllib.error.HTTPError as e:
            sys.exit(f"{method} {path} -> HTTP {e.code} : {e.read().decode()[:600]}")
        if raw:
            return txt
        return json.loads(txt) if txt else {}

    # ------------------------------------------------------------------ navigation
    def root(self) -> str:
        return self.call("GET", "/flow/process-groups/root")["processGroupFlow"]["id"]

    def groupe(self, nom: str) -> str:
        for pg in self.call("GET", f"/process-groups/{self.root()}/process-groups")["processGroups"]:
            if pg["component"]["name"] == nom:
                return pg["id"]
        sys.exit(f"Process Group introuvable : {nom}")

    def processeurs(self, pg: str) -> list[dict]:
        return self.call("GET", f"/process-groups/{pg}/processors")["processors"]

    def processeur(self, pg: str, nom: str) -> dict:
        for p in self.processeurs(pg):
            if p["component"]["name"] == nom:
                return p
        sys.exit(f"processeur introuvable : {nom}")

    # ------------------------------------------------------------------ construction
    def creer_groupe(self, nom: str, x: float, y: float) -> str:
        for pg in self.call("GET", f"/process-groups/{self.root()}/process-groups")["processGroups"]:
            if pg["component"]["name"] == nom:
                sys.exit(f"le Process Group « {nom} » existe déjà : rien n'est recréé (pas de doublon)")
        r = self.call("POST", f"/process-groups/{self.root()}/process-groups",
                      {"revision": {"version": 0}, "component": {"name": nom, "position": {"x": x, "y": y}}})
        return r["id"]

    def ajouter(self, pg: str, typ: str, nom: str, x: float, y: float, props: dict,
                auto_term: list[str] = (), periode: str | None = None, commentaire: str = "") -> str:
        r = self.call("POST", f"/process-groups/{pg}/processors", {"revision": {"version": 0}, "component": {
            "type": P[typ], "name": nom, "position": {"x": x, "y": y}}})
        cfg = {"properties": props, "autoTerminatedRelationships": list(auto_term), "comments": commentaire}
        if periode:
            cfg["schedulingPeriod"] = periode
        self.call("PUT", f"/processors/{r['id']}", {"revision": r["revision"],
                                                    "component": {"id": r["id"], "config": cfg}})
        return r["id"]

    def relier(self, pg: str, src: str, dst: str, rels: list[str], nom: str = "") -> str:
        r = self.call("POST", f"/process-groups/{pg}/connections", {"revision": {"version": 0}, "component": {
            "name": nom, "source": {"id": src, "groupId": pg, "type": "PROCESSOR"},
            "destination": {"id": dst, "groupId": pg, "type": "PROCESSOR"}, "selectedRelationships": rels}})
        return r["id"]

    # ------------------------------------------------------------------ exécution
    def etat_groupe(self, pg: str, etat: str) -> None:
        self.call("PUT", f"/flow/process-groups/{pg}", {"id": pg, "state": etat})

    def etat_proc(self, pid: str, etat: str) -> None:
        p = self.call("GET", f"/processors/{pid}")
        self.call("PUT", f"/processors/{pid}/run-status", {"revision": p["revision"], "state": etat})

    def config(self, pid: str, props: dict) -> dict:
        p = self.call("GET", f"/processors/{pid}")
        return self.call("PUT", f"/processors/{pid}", {"revision": p["revision"],
                                                       "component": {"id": pid, "config": {"properties": props}}})


# ====================================================================== flux
def flux_obligatoire(n: NiFi) -> None:
    """Étape 8 : GetFile -> PutHDFS. failure conservée et reliée à LogAttribute (diagnostic visible)."""
    pg = n.creer_groupe(G_OBLIGATOIRE, 0, 0)
    get = n.ajouter(pg, "GetFile", "GetFile - lecture /data/nifi/input", 0, 0, {
        "Input Directory": "/data/nifi/input",
        "Keep Source File": "false",          # fichier consommé après lecture réussie (copie de travail)
        "Recurse Subdirectories": "false",
    }, periode="10 sec", commentaire="Lit la copie de travail déposée dans /data/nifi/input (jamais l'original du kit).")
    put = n.ajouter(pg, "PutHDFS", "PutHDFS - ecriture /retail-lake/raw/nifi", 0, 260, {
        "Hadoop Configuration Resources": HADOOP_CONF,
        "Directory": "/retail-lake/raw/nifi",
        "Conflict Resolution Strategy": "fail",  # jamais d'écrasement silencieux : le conflit part en failure
    }, auto_term=["success"], commentaire="success auto-terminé : le dépôt HDFS est la fin du flux.")
    log = n.ajouter(pg, "LogAttribute", "LogAttribute - diagnostic des echecs", 760, 260, {
        "Log Level": "warn", "Log Payload": "false", "Attributes to Log Regular Expression": ".*",
        "Log Prefix": "ECHEC-PutHDFS ",
    }, commentaire="Rend visibles dans nifi-app.log les attributs des FlowFiles en échec.")
    n.relier(pg, get, put, ["success"])
    n.relier(pg, put, log, ["failure"], "echecs PutHDFS")
    # sortie de LogAttribute : file d'attente conservée vers un PutFile d'erreur (rien n'est supprimé sans examen)
    err = n.ajouter(pg, "PutFile", "PutFile - quarantaine locale /data/nifi/error", 760, 520, {
        "Directory": "/data/nifi/error", "Conflict Resolution Strategy": "fail"},
        auto_term=["success", "failure"], commentaire="Conserve le contenu des échecs pour reprise manuelle.")
    n.relier(pg, log, err, ["success"])
    print(f"flux obligatoire créé : groupe {pg}")


def flux_enrichi(n: NiFi) -> None:
    """Étape 12 + AV-01 (multi-fichiers), AV-02 (routage), AV-03 (reprises), AV-04 (contrôles avant ingestion)."""
    pg = n.creer_groupe(G_ENRICHI, 700, 0)
    get = n.ajouter(pg, "GetFile", "GetFile - lot /data/nifi/lot", 0, 0, {
        "Input Directory": "/data/nifi/lot", "Keep Source File": "false", "Recurse Subdirectories": "true",
        "File Filter": ".*",  # tout est lu, y compris les fichiers cachés : le tri est fait par les contrôles
        "Ignore Hidden Files": "false",
    }, periode="15 sec")
    attrs = n.ajouter(pg, "UpdateAttribute", "UpdateAttribute - attributs de suivi", 0, 220, {
        "tpcxbb.table": "${filename:substringBeforeLast('.')}",
        "tpcxbb.lot": "${path:contains('refresh'):ifElse('refresh','initial')}",
        "tpcxbb.extension": "${filename:substringAfterLast('.'):toLower()}",
        "ingestion.flux": "uc04-enrichi",
        "ingestion.date": "${now():format('yyyy-MM-dd')}",
        "ingestion.horodatage": "${now():format(\"yyyy-MM-dd'T'HH:mm:ss.SSSZ\")}",
        "source.chemin": "${absolute.path}${filename}",
    })
    sha = n.ajouter(pg, "CryptographicHashContent", "CryptographicHashContent - SHA-256", 0, 440, {
        "Hash Algorithm": "SHA-256", "Fail When Content Empty": "false"}, auto_term=["failure"])
    ctrl = n.ajouter(pg, "RouteOnAttribute", "RouteOnAttribute - controles avant ingestion", 0, 660, {
        "Routing Strategy": "Route to 'match' if all match",
        "taille_non_nulle": "${fileSize:gt(0)}",
        "extension_attendue": "${tpcxbb.extension:matches('dat|csv')}",
        "nom_lisible": "${filename:matches('[A-Za-z0-9_]+\\.[A-Za-z0-9]+')}",
    }, commentaire="AV-04 : présence (GetFile), taille > 0, extension .dat/.csv, nom exploitable.")
    route = n.ajouter(pg, "RouteOnAttribute", "RouteOnAttribute - routage par domaine", 0, 880, {
        "Routing Strategy": "Route to Property name",
        # règles fondées sur l'inventaire réel (UC-01/UC-03) : le nom du fichier est le nom de la table
        "ventes": "${tpcxbb.table:matches('store_sales|web_sales')}",
        "retours": "${tpcxbb.table:matches('store_returns|web_returns')}",
        "clients": "${tpcxbb.table:matches('customer|customer_address|customer_demographics|household_demographics|income_band')}",
        "produits": "${tpcxbb.table:matches('item|item_marketprices|item_marketprices_audit')}",
        "stocks": "${tpcxbb.table:equals('inventory')}",
        "navigation": "${tpcxbb.table:matches('web_clickstreams|web_page|web_site')}",
        "avis": "${tpcxbb.table:equals('product_reviews')}",
        "referentiels": "${tpcxbb.table:matches('date_dim|time_dim|store|warehouse|promotion|reason|ship_mode')}",
    }, commentaire="AV-02 : domaine dans RouteOnAttribute.Route ; fichier non reconnu -> unmatched -> rejet.")
    put = n.ajouter(pg, "PutHDFS", "PutHDFS - raw/nifi/<domaine>/<lot>/<table>", 520, 880, {
        "Hadoop Configuration Resources": HADOOP_CONF,
        "Directory": "/retail-lake/raw/nifi/${RouteOnAttribute.Route}/${tpcxbb.lot}/${tpcxbb.table}",
        "Conflict Resolution Strategy": "fail",
    }, auto_term=["success"])
    retry = n.ajouter(pg, "RetryFlowFile", "RetryFlowFile - 3 tentatives", 1040, 880, {
        "Maximum Retries": "3", "Penalize Retries": "true", "Retry Attribute": "ingestion.tentatives"},
        commentaire="AV-03 : échec temporaire (HDFS indisponible) -> nouvelle tentative pénalisée, compteur en attribut.")
    rej_ctrl = n.ajouter(pg, "UpdateAttribute", "UpdateAttribute - motif rejet controle", -520, 880, {
        "rejet.motif": "controle_avant_ingestion (taille nulle, extension ou nom non conforme)"})
    rej_dom = n.ajouter(pg, "UpdateAttribute", "UpdateAttribute - motif rejet domaine", -520, 1100, {
        "rejet.motif": "fichier_non_reconnu (aucun domaine TPCx-BB)"})
    rej_put = n.ajouter(pg, "UpdateAttribute", "UpdateAttribute - motif echec depot", 1040, 1100, {
        "rejet.motif": "echec_depot_hdfs apres ${ingestion.tentatives:replaceNull(0)} tentative(s)"})
    log = n.ajouter(pg, "LogAttribute", "LogAttribute - journal des rejets", 0, 1320, {
        "Log Level": "warn", "Log Payload": "false", "Attributes to Log Regular Expression": ".*",
        "Log Prefix": "REJET-UC04 "})
    quar = n.ajouter(pg, "PutFile", "PutFile - /data/nifi/error/<date>", 0, 1540, {
        "Directory": "/data/nifi/error/${ingestion.date}", "Conflict Resolution Strategy": "fail",
        "Create Missing Directories": "true"}, auto_term=["success", "failure"])

    n.relier(pg, get, attrs, ["success"])
    n.relier(pg, attrs, sha, ["success"])
    n.relier(pg, sha, ctrl, ["success"])
    n.relier(pg, ctrl, route, ["matched"], "conforme")
    n.relier(pg, ctrl, rej_ctrl, ["unmatched"], "non conforme")
    n.relier(pg, route, put, ["ventes", "retours", "clients", "produits", "stocks", "navigation", "avis",
                              "referentiels"], "fichier reconnu")
    n.relier(pg, route, rej_dom, ["unmatched"], "fichier non reconnu")
    n.relier(pg, put, retry, ["failure"], "echec depot")
    n.relier(pg, retry, put, ["retry"], "nouvelle tentative")
    n.relier(pg, retry, rej_put, ["retries_exceeded"], "tentatives epuisees")
    n.relier(pg, retry, rej_put, ["failure"], "erreur retry")
    for src in (rej_ctrl, rej_dom, rej_put):
        n.relier(pg, src, log, ["success"])
    n.relier(pg, log, quar, ["success"])
    print(f"flux enrichi créé : groupe {pg}")


# ====================================================================== preuves
def etat(n: NiFi, pg: str) -> None:
    st = n.call("GET", f"/flow/process-groups/{pg}/status?recursive=false")["processGroupStatus"]["aggregateSnapshot"]
    print(f"Process Group : {st['name']}")
    print(f"{'processeur':<52}{'état':<10}{'entrés':>8}{'sortis':>8}{'lus':>12}{'écrits':>12}")
    for p in st["processorStatusSnapshots"]:
        s = p["processorStatusSnapshot"]
        print(f"{s['name'][:51]:<52}{s['runStatus']:<10}{s['flowFilesIn']:>8}{s['flowFilesOut']:>8}"
              f"{s['read']:>12}{s['written']:>12}")
    print(f"\n{'connexion (source -> destination)':<84}{'en file':>10}")
    for c in st["connectionStatusSnapshots"]:
        s = c["connectionStatusSnapshot"]
        nom = f"{s['sourceName']} -> {s['destinationName']}"
        print(f"{nom[:83]:<84}{s['queued']:>10}")
    invalides = [(p["component"]["name"], p["component"].get("validationErrors"))
                 for p in n.processeurs(pg) if p["component"].get("validationErrors")]
    print("\nprocesseurs invalides : " + ("aucun" if not invalides else ""))
    for nom, errs in invalides:
        for e in errs:
            print(f"  - {nom} : {e}")


def provenance(n: NiFi, nom: str | None, sortie: str | None) -> None:
    req = {"maxResults": 1000, "summarize": False, "incrementalResults": False}
    if nom:
        req["searchTerms"] = {"Filename": {"value": nom, "inverse": False}}
    q = n.call("POST", "/provenance", {"provenance": {"request": req}})["provenance"]
    while not q["finished"]:
        time.sleep(0.5)
        q = n.call("GET", f"/provenance/{q['id']}")["provenance"]
    n.call("DELETE", f"/provenance/{q['id']}")
    evts = sorted(q["results"]["provenanceEvents"], key=lambda e: int(e["eventId"]))
    print(f"{'id':>4}  {'horodatage':<28}{'type':<21}{'composant':<46}{'fichier':<26}{'taille':>10}  uuid FlowFile")
    for e in evts:
        print(f"{e['eventId']:>4}  {e['eventTime']:<28}{e['eventType']:<21}{e['componentName'][:45]:<46}"
              f"{e.get('attributes') and next((a['value'] for a in e['attributes'] if a['name']=='filename'), '') or '':<26}"
              f"{e['fileSizeBytes']:>10}  {e['flowFileUuid']}"
              + (f"\n      transit : {e['transitUri']}" if e.get("transitUri") else "")
              + (f"\n      détails : {e['details']}" if e.get("details") else ""))
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump(evts, f, ensure_ascii=False, indent=2)
        print(f"\n{len(evts)} événements exportés dans {sortie}")


def lignage(n: NiFi, event_id: str, sortie: str | None) -> None:
    ev = n.call("GET", f"/provenance-events/{event_id}")["provenanceEvent"]
    q = n.call("POST", "/provenance/lineage", {"lineage": {"request": {
        "eventId": int(event_id), "lineageRequestType": "FLOWFILE", "uuid": ev["flowFileUuid"]}}})["lineage"]
    while not q["finished"]:
        time.sleep(0.5)
        q = n.call("GET", f"/provenance/lineage/{q['id']}")["lineage"]
    n.call("DELETE", f"/provenance/lineage/{q['id']}")
    nodes = sorted(q["results"]["nodes"], key=lambda x: x.get("millis", 0))
    print(f"Lignage du FlowFile {ev['flowFileUuid']} (fichier {next((a['value'] for a in ev['attributes'] if a['name']=='filename'), '?')})")
    for nd in nodes:
        if nd["type"] == "EVENT":
            print(f"  {nd['timestamp']:<26} {nd['eventType']:<10} événement {nd['id']}")
        else:
            print(f"  FlowFile {nd['flowFileUuid']}")
    if sortie:
        with open(sortie, "w", encoding="utf-8") as f:
            json.dump({"evenement": ev, "lignage": q["results"]}, f, ensure_ascii=False, indent=2)


def bulletins(n: NiFi) -> None:
    for b in n.call("GET", "/flow/bulletin-board?limit=50")["bulletinBoard"]["bulletins"]:
        bb = b.get("bulletin")
        if bb:
            print(f"{bb['timestamp']}  {bb['level']:<6} {bb.get('sourceName', '')} : {bb['message'][:400]}")


def vider(n: NiFi, pg: str) -> None:
    for c in n.call("GET", f"/process-groups/{pg}/connections")["connections"]:
        if c["status"]["aggregateSnapshot"]["flowFilesQueued"]:
            n.call("POST", f"/flowfile-queues/{c['id']}/drop-requests")


def main(argv: list[str]) -> None:
    if not argv:
        sys.exit(__doc__)
    n, cmd, a = NiFi(), argv[0], argv[1:]
    noms = {"obligatoire": G_OBLIGATOIRE, "enrichi": G_ENRICHI}
    g = lambda s: n.groupe(noms.get(s, s))  # noqa: E731
    if cmd == "obligatoire":
        flux_obligatoire(n)
    elif cmd == "enrichi":
        flux_enrichi(n)
    elif cmd in ("demarrer", "arreter"):
        n.etat_groupe(g(a[0]), "RUNNING" if cmd == "demarrer" else "STOPPED")
        time.sleep(1.5)
        for p in n.processeurs(g(a[0])):
            print(f"{p['component']['name']} : {p['status']['aggregateSnapshot']['runStatus']}")
    elif cmd in ("demarrer-proc", "arreter-proc"):
        p = n.processeur(g(a[0]), a[1])
        demande = "RUNNING" if cmd == "demarrer-proc" else "STOPPED"
        n.etat_proc(p["id"], demande)
        time.sleep(1.5)  # l'API accepte la demande même si le processeur est invalide : on relit l'état réel
        r = n.call("GET", f"/processors/{p['id']}")
        print(f"{a[1]} : demandé {demande} -> état réel {r['status']['aggregateSnapshot']['runStatus']} "
              f"(validation {r['component'].get('validationStatus')})")
    elif cmd == "etat":
        etat(n, g(a[0]))
    elif cmd == "config":
        p = n.processeur(g(a[0]), a[1])
        r = n.config(p["id"], {a[2]: a[3]})
        print(f"{a[1]} : {a[2]} = {a[3]}")
        for e in r["component"].get("validationErrors") or []:
            print(f"  validation : {e}")
    elif cmd == "provenance":
        nom = a[a.index("--nom") + 1] if "--nom" in a else None
        out = a[a.index("--json") + 1] if "--json" in a else None
        provenance(n, nom, out)
    elif cmd == "lignage":
        lignage(n, a[0], a[a.index("--json") + 1] if "--json" in a else None)
    elif cmd == "bulletins":
        bulletins(n)
    elif cmd == "exporter":
        txt = n.call("GET", f"/process-groups/{g(a[0])}/download?includeReferencedServices=true", raw=True)
        with open(a[1], "w", encoding="utf-8") as f:
            f.write(json.dumps(json.loads(txt), ensure_ascii=False, indent=2))
        print(f"définition du flux exportée : {a[1]}")
    elif cmd == "vider":
        vider(n, g(a[0]))
    elif cmd == "supprimer":  # groupe arrêté : files vidées puis suppression (reconstruction propre)
        pg = g(a[0]); n.etat_groupe(pg, "STOPPED"); vider(n, pg); time.sleep(2)
        r = n.call("GET", f"/process-groups/{pg}")
        n.call("DELETE", f"/process-groups/{pg}?version={r['revision']['version']}")
        print(f"groupe supprimé : {noms.get(a[0], a[0])}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
