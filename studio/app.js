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
 const btn=document.getElementById("probe"), o=document.getElementById("probe-output");
 btn.disabled=true; o.textContent="启动中…";
 try{
  const r=await fetch("/api/codex-probe",{method:"POST",
   headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},body:"{}"});
  const data=await r.json();
  if(!r.ok){o.textContent=data.error||JSON.stringify(data);btn.disabled=false;return;}
  const poll=async()=>{
   try{
    const item=await fetch("/api/codex-probe").then(r=>r.json());
    o.textContent="状态："+item.status+(item.status==="running"?" · 已运行 "+item.elapsed_seconds+" 秒（含网络重试）":"")+"\\n"+(item.output||"");
    if(item.status==="running"){setTimeout(poll,1500);} else {btn.disabled=false;}
   }catch(e){o.textContent=String(e);btn.disabled=false;}
  };
  poll();
 }catch(e){o.textContent=String(e);btn.disabled=false;}
});
init().catch(e=>document.getElementById("workspaces").textContent=String(e));
