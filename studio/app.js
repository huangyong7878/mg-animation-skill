let csrf="";
async function init(){
 const [s,t]=await Promise.all([fetch("/api/status").then(r=>r.json()),fetch("/api/csrf").then(r=>r.json())]);
 csrf=t.token;
 document.getElementById("project").textContent=s.project;
 document.getElementById("codex").textContent=s.codex_installed?"Codex CLI 已安装":"尚未检测到 Codex CLI";
 document.getElementById("workspaces").replaceChildren();
 const parent=document.getElementById("workspaces");
 if(!s.workspaces.length){parent.textContent="暂无已初始化工作区";return;}
 for(const w of s.workspaces){const item=document.createElement("div");item.className="item";item.textContent=w.name+" · "+w.status+" · Attempt "+w.attempt;parent.append(item);}
}
document.getElementById("probe").addEventListener("click",async()=>{
 const btn=document.getElementById("probe");btn.disabled=true;
 const o=document.getElementById("probe-output");o.textContent="执行只读探针中…";
 try{const r=await fetch("/api/codex-probe",{method:"POST",headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},body:"{}"});
 const data=await r.json();o.textContent=data.output||data.error||JSON.stringify(data);}
 catch(e){o.textContent=String(e);}finally{btn.disabled=false;}
});
init().catch(e=>document.getElementById("workspaces").textContent=String(e));
