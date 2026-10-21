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

document.getElementById("run-r4").addEventListener("click",async()=>{
 const checkbox=document.getElementById("confirm-r4");
 const out=document.getElementById("r4-output");
 if(!checkbox.checked){out.textContent="请先确认返工执行范围和可能的模型用量。";return;}
 const selected=document.getElementById("task-select").value;
 if(!selected){out.textContent="没有可执行任务；请由 R0 使用新版契约重新派发。";return;}
 const btn=document.getElementById("run-r4");
 btn.disabled=true;
 try{
  const resp=await fetch("/api/r4/start",{method:"POST",headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},body:JSON.stringify({task_id:selected})});
  const result=await resp.json();
  if(!resp.ok){out.textContent=result.error||JSON.stringify(result);btn.disabled=false;return;}
  const poll=async()=>{
   try{
    const data=await fetch("/api/r4").then(r=>r.json());
    out.textContent="状态："+data.status+"\n"+(data.output||"")+
       (data.result?"\n工作目录："+data.result.worktree+"\n改动文件："+JSON.stringify(data.result.changed_files):"");
    if(data.status==="running"){setTimeout(poll,1800);}
   }catch(e){out.textContent=String(e);}
  };
  poll();
 }catch(e){out.textContent=String(e);}
});

async function loadTasks(){
 const select=document.getElementById("task-select");
 try{
  const result=await fetch("/api/r4/tasks").then(r=>r.json());
  select.replaceChildren();
  for(const task of result.tasks){
    const opt=document.createElement("option");
    opt.value=task.id;
    opt.textContent=task.project+" / "+task.id+" ("+task.findings+" 项)";
    select.append(opt);
  }
  if(!result.tasks.length){const opt=document.createElement("option");opt.textContent="暂无新版契约的可执行任务";opt.value="";select.append(opt);}
 }catch(e){select.replaceChildren();select.textContent="加载任务失败";}
}
loadTasks();

async function refreshHistory(){
 const target=document.getElementById("job-history");
 try{
  const response=await fetch("/api/r4/history");
  if(!response.ok)throw new Error("HTTP "+response.status);
  const data=await response.json();
  target.replaceChildren();
  if(!data.jobs.length){target.textContent="尚无 R4 运行记录";return;}
  for(const job of data.jobs){
   const item=document.createElement("div");item.className="item";
   item.textContent="#"+job.id+" · "+job.task_id+" · "+job.status;
   target.append(item);
  }
 }catch(error){target.textContent="读取历史失败："+String(error);}
}
document.getElementById("refresh-history").addEventListener("click",refreshHistory);
refreshHistory();

let deliveryReady=false;
const deliveryOutput=document.getElementById("delivery-output");
const deliveryBuild=document.getElementById("delivery-build");
function canBuild(){deliveryBuild.disabled=!deliveryReady||!document.getElementById("delivery-confirm").checked;}
document.getElementById("delivery-confirm").addEventListener("change",canBuild);
document.getElementById("delivery-check").addEventListener("click",async()=>{
 deliveryReady=false;canBuild();deliveryOutput.textContent="正在校验双锁和输入媒体…";
 try{
  const result=await fetch("/api/delivery/preflight").then(r=>r.json());
  deliveryReady=result.ready;
  deliveryOutput.textContent=result.ready?
   "PASS · 源码："+result.source_sha+"\\n已锁定媒体校验通过。成片仍需独立 R5 审核。":
   "BLOCKED\\n"+result.issues.join("\\n");
  canBuild();
 }catch(e){deliveryOutput.textContent=String(e);}
});
deliveryBuild.addEventListener("click",async()=>{
 if(!deliveryReady||!document.getElementById("delivery-confirm").checked)return;
 deliveryBuild.disabled=true;deliveryReady=false;
 deliveryOutput.textContent="正在启动正式构建…";
 try{
  const resp=await fetch("/api/delivery/build",{method:"POST",headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},body:"{}"});
  const info=await resp.json();
  if(!resp.ok){deliveryOutput.textContent=info.issues?.join("\\n")||info.error||"构建已阻断";return;}
  const poll=async()=>{
   try{
    const result=await fetch("/api/delivery/status").then(r=>r.json());
    deliveryOutput.textContent="状态："+result.status+"\\n"+JSON.stringify(result.result||{},null,2);
    if(result.status==="running")setTimeout(poll,2000);
   }catch(e){deliveryOutput.textContent=String(e);}
  };poll();
 }catch(e){deliveryOutput.textContent=String(e);}
});

async function refreshDeliveries(){
 const list=document.getElementById("delivery-list");
 const details=document.getElementById("delivery-details");
 const video=document.getElementById("delivery-video");
 video.pause();video.removeAttribute("src");video.hidden=true;details.textContent="";
 try{
  const response=await fetch("/api/deliveries");
  if(!response.ok)throw Error("HTTP "+response.status);
  const data=await response.json();
  list.replaceChildren();
  if(!data.deliveries.length){list.textContent="暂无 Stage D 本地交付包";return;}
  for(const item of data.deliveries){
   const row=document.createElement("div");row.className="item";
   const label=document.createElement("span");
   label.textContent=item.id+" · "+item.status+" · "+(item.manifest_ok?"SHA256 校验通过":"完整性校验失败");
   row.append(label);
   if(item.manifest_ok&&item.video_url){
    const button=document.createElement("button");button.type="button";
    button.style.marginLeft="12px";button.textContent="查看视频";
    button.addEventListener("click",()=>{
      video.src=item.video_url;video.hidden=false;video.load();
      details.textContent="实现版本："+item.source_sha+"\n导演规格："+item.spec_sha256+
       "\n媒体文件："+item.media_count+"\nR5 尚未通过；R7 未授权。";
    });
    row.append(button);
   }else{
    const note=document.createElement("pre");note.textContent=(item.errors||[]).join("\n");row.append(note);
   }
   list.append(row);
  }
 }catch(e){list.textContent="读取交付包失败："+String(e);}
}
document.getElementById("refresh-deliveries").addEventListener("click",refreshDeliveries);
refreshDeliveries();
