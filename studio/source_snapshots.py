"""Content-addressed, immutable-by-policy R4 working tree snapshots.

A snapshot is an audit artifact, not an authorized Stage D delivery.
No Git commit/push or change to formal production lock gates.
"""
import hashlib
import json
import os
import shutil
import stat
from pathlib import Path

def hash_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as stream:
        for block in iter(lambda:stream.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def snapshot(repo, tree, *, base_commit, allowed_files, changed_files, approved_finding_ids):
    from studio.r4_runner import valid_path
    repo=Path(repo).resolve()
    tree=Path(tree).resolve()
    changed=sorted(set(changed_files))
    allowed=set(allowed_files)
    if not changed or any(p not in allowed or not valid_path(p) for p in changed):
        raise ValueError("Snapshot requires nonempty changed files within approved edit scope")
    entries=[]
    for name in changed:
        source=tree/name
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(tree):
            raise ValueError("Snapshot source file invalid: "+name)
        if source.stat().st_size > 10*1024*1024:
            raise ValueError("Snapshot source file exceeds 10MB")
        entries.append({"path":name,"size":source.stat().st_size,"sha256":hash_file(source)})
    content={"schema_version":"1.0","kind":"r4_source_snapshot",
             "base_commit":base_commit,"approved_finding_ids":sorted(set(approved_finding_ids)),
             "files":entries,"stage":"preproduction_review_only",
             "formal_stage_d_authorized":False,"r5_pass":False,"r7_authorized":False}
    digest=hashlib.sha256(canonical(content)).hexdigest()
    snapshots=repo/"work/mg_studio/snapshots"
    destination=snapshots/digest
    if destination.exists():
        if verify(repo,digest)["valid"]:
            return {"snapshot_id":digest,"path":str(destination),"reused":True}
        raise ValueError("Existing snapshot has failed integrity verification")
    snapshots.mkdir(parents=True,exist_ok=True)
    temporary=snapshots/("."+digest+".writing")
    temporary.mkdir(exist_ok=False)
    try:
        for entry in entries:
            dest=temporary/"source"/entry["path"]
            dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(tree/entry["path"],dest,follow_symlinks=False)
            os.chmod(dest,0o444)
        (temporary/"manifest.json").write_bytes(canonical(content))
        os.chmod(temporary/"manifest.json",0o444)
        temporary.rename(destination)
        os.chmod(destination,0o555)
    except BaseException:
        shutil.rmtree(temporary,ignore_errors=True)
        raise
    return {"snapshot_id":digest,"path":str(destination),"reused":False}

def verify(repo,snapshot_id):
    if not isinstance(snapshot_id,str) or len(snapshot_id)!=64 or any(c not in "0123456789abcdef" for c in snapshot_id):
        raise ValueError("Invalid snapshot ID")
    root=(Path(repo).resolve()/"work/mg_studio/snapshots").resolve()
    folder=(root/snapshot_id).resolve()
    if not folder.is_relative_to(root):
        raise ValueError("Snapshot path escapes root")
    manifest=folder/"manifest.json"
    if not manifest.is_file():
        return {"valid":False,"reason":"manifest missing"}
    try:
        data=json.loads(manifest.read_text())
        if hashlib.sha256(canonical(data)).hexdigest()!=snapshot_id:
            return {"valid":False,"reason":"manifest digest mismatch"}
        if data.get("kind")!="r4_source_snapshot" or data.get("formal_stage_d_authorized") is not False:
            return {"valid":False,"reason":"invalid snapshot type"}
        from studio.r4_runner import valid_path
        names=[entry["path"] for entry in data["files"]]
        if len(set(names))!=len(names):
            return {"valid":False,"reason":"duplicate paths"}
        for entry in data["files"]:
            name=entry["path"]
            p=folder/"source"/name
            if not valid_path(name) or p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(folder):
                return {"valid":False,"reason":"invalid source path"}
            if p.stat().st_size!=entry["size"] or hash_file(p)!=entry["sha256"]:
                return {"valid":False,"reason":"source hash mismatch"}
        return {"valid":True,"snapshot_id":snapshot_id,"base_commit":data["base_commit"],
                "changed_files":names,"approved_finding_ids":data["approved_finding_ids"],
                "formal_stage_d_authorized":False}
    except (ValueError,KeyError,TypeError,OSError):
        return {"valid":False,"reason":"malformed snapshot"}
