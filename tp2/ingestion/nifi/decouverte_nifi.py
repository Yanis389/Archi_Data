#!/usr/bin/env python3
"""Étape 6 - Découverte de l'instance NiFi : version, état, composants disponibles pour l'ingestion."""
import sys
sys.path.insert(0, "/work/ingestion/nifi")
from nifi_flux import NiFi  # noqa: E402

n = NiFi()
about = n.call("GET", "/flow/about")["about"]
print(f"Produit : {about['title']} {about['version']}  |  build {about.get('buildRevision', '?')[:10]}  |  fuseau {about.get('timezone')}")
print(f"URI : {about.get('uri')}")
st = n.call("GET", "/flow/status")["controllerStatus"]
print(f"État du contrôleur : threads actifs={st['activeThreadCount']}  FlowFiles en file={st['flowFilesQueued']}  "
      f"processeurs en marche={st['runningCount']} arrêtés={st['stoppedCount']} invalides={st['invalidCount']}")
diag = n.call("GET", "/system-diagnostics")["systemDiagnostics"]["aggregateSnapshot"]
print(f"JVM : tas utilisé {diag['usedHeap']} / max {diag['maxHeap']}  |  processeurs {diag['availableProcessors']}  |  "
      f"uptime {diag['uptime']}")
for r in [diag["flowFileRepositoryStorageUsage"]] + diag["contentRepositoryStorageUsage"] + diag["provenanceRepositoryStorageUsage"]:
    print(f"  dépôt {r.get('identifier', 'flowfile'):<10} libre {r['freeSpace']:>10}  utilisé {r['utilization']}")
types = n.call("GET", "/flow/processor-types")["processorTypes"]
print(f"\nTypes de processeurs disponibles : {len(types)}")
utiles = ["GetFile", "ListFile", "FetchFile", "PutHDFS", "ListHDFS", "FetchHDFS", "GetHDFSFileInfo", "UpdateAttribute",
          "RouteOnAttribute", "LogAttribute", "PutFile", "CryptographicHashContent", "RetryFlowFile", "ValidateRecord",
          "ValidateCsv", "DetectDuplicate"]
for u in utiles:
    t = next((t for t in types if t["type"].endswith("." + u)), None)
    print(f"  {u:<26}" + (f"disponible  ({t['bundle']['artifact']} {t['bundle']['version']})" if t else "ABSENT"))
cs = n.call("GET", "/flow/controller-service-types")["controllerServiceTypes"]
print(f"\nTypes de Controller Services disponibles : {len(cs)}  (ex. : " +
      ", ".join(sorted(c["type"].split(".")[-1] for c in cs if "CSV" in c["type"] or "MapCache" in c["type"])[:6]) + ")")
