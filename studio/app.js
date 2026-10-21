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
  const wrapper=document.createElement("div");wrapper.className="table-scroll";
  const table=document.createElement("table");table.className="deliveries-table";
  const header=document.createElement("thead");
  const headerRow=document.createElement("tr");
  for(const title of ["版本","创建时间","交付状态","R5 审核","媒体校验","操作"]){
    const th=document.createElement("th");th.textContent=title;headerRow.append(th);
  }
  header.append(headerRow);table.append(header);
  const body=document.createElement("tbody");
  for(const item of data.deliveries){
   const row=document.createElement("tr");
   const addCell=value=>{const cell=document.createElement("td");cell.textContent=value;row.append(cell);return cell;};
   const version=addCell(item.version||item.id);
   const sub=document.createElement("small");sub.textContent=item.id;version.append(document.createElement("div"),sub);
   const creation=item.time?new Date(item.time).toLocaleString("zh-CN"):"未知";
   addCell(creation);
   addCell(item.status||"未知");
   addCell(item.review_status||"未确认");
   addCell(item.manifest_ok?"SHA256 通过":"校验失败");
   const actions=addCell("");
   if(item.manifest_ok&&item.video_url){
     const button=document.createElement("button");button.type="button";button.textContent="查看视频";
     button.addEventListener("click",()=>{
       video.src=item.video_url;video.hidden=false;video.load();
       details.textContent="交付："+item.id+"\n创建时间："+creation+
        "\n时间来源："+(item.time_basis==="filesystem_birthtime"?"文件系统创建时间":"未知")+
        "\n实现版本："+item.source_sha+"\n导演规格："+item.spec_sha256+
        "\n媒体文件："+item.media_count+"\nR5："+item.review_status+"；R7 未授权。";
     });
     actions.append(button);
   }else{
     const note=document.createElement("small");note.textContent=(item.errors||[]).join("; ")||"不可播放";actions.append(note);
   }
   body.append(row);
  }
  table.append(body);wrapper.append(table);list.append(wrapper);
 }catch(e){list.textContent="读取交付包失败："+String(e);}
}
document.getElementById("refresh-deliveries").addEventListener("click",refreshDeliveries);
refreshDeliveries();

async function refreshR5(){
 const root=document.getElementById("r5-history");root.textContent="加载中…";
 try{
  const response=await fetch("/api/r5/history");
  if(!response.ok)throw new Error("HTTP "+response.status);
  const records=(await response.json()).reviews;
  root.replaceChildren();
  if(!records.length){root.textContent="还没有可核验来源的 DeepSeek 审核记录";return;}
  for(const record of records){
   const box=document.createElement("div");box.className="item";
   const label=document.createElement("strong");label.textContent=record.id+" · "+record.scope;
   box.append(label);
   const meta=document.createElement("p");
   meta.textContent="R0："+record.r0_status+" · 音频未审核 · 连续运动未审核 · 正式 R5 Pending";
   box.append(meta);
   const details=document.createElement("details");
   const summary=document.createElement("summary");
   summary.textContent="查看审核证据与观察意见";
   details.append(summary);
   const provenance=document.createElement("p");
   provenance.textContent="源码："+(record.source_sha||"未知")+" · 视频 SHA256："+(record.video_sha256||"未知")+
      " · 抽帧："+(record.sampled_frames??"未知")+" · Token："+(record.token_usage??"未知");
   details.append(provenance);
   const observations=document.createElement("pre");
   observations.textContent=record.observations;
   details.append(observations);box.append(details);root.append(box);
  }
 }catch(e){root.textContent="审核记录加载失败："+String(e);}
}
document.getElementById("r5-refresh").addEventListener("click",refreshR5);
refreshR5();

let r5Ready=false;
const r5Select=document.getElementById("r5-delivery-select");
const r5Submit=document.getElementById("r5-submit");
const r5Output=document.getElementById("r5-submit-output");
function updateR5Button(){r5Submit.disabled=!r5Ready||!document.getElementById("r5-paid-confirm").checked;}
r5Select.addEventListener("change",()=>{r5Ready=false;updateR5Button();r5Output.textContent="";});
document.getElementById("r5-paid-confirm").addEventListener("change",updateR5Button);
async function loadR5Deliveries(){
 try{
  const list=await fetch("/api/deliveries").then(r=>r.json());
  r5Select.replaceChildren();
  for(const item of list.deliveries){
   if(!item.manifest_ok||item.status!=="ready_for_qa")continue;
   const o=document.createElement("option");o.value=item.id;o.textContent=item.version+" · "+item.id;r5Select.append(o);
  }
  if(!r5Select.options.length){const o=document.createElement("option");o.value="";o.textContent="暂无可审核成片";r5Select.append(o);}
 }catch(e){r5Output.textContent=String(e);}
}
document.getElementById("r5-preflight").addEventListener("click",async()=>{
 r5Ready=false;updateR5Button();
 if(!r5Select.value){r5Output.textContent="请选择交付包";return;}
 try{
  const check=await fetch("/api/r5/preflight/"+encodeURIComponent(r5Select.value)).then(r=>r.json());
  r5Ready=check.ready===true;
  r5Output.textContent=r5Ready?
   "PASS · 已绑定源码 "+check.source_sha+"\n仅进行收费抽帧审核，完整音画审核仍需独立完成。":
   "BLOCKED · "+(check.issues||[check.error||"校验失败"]).join("; ");
  updateR5Button();
 }catch(e){r5Output.textContent=String(e);}
});
r5Submit.addEventListener("click",async()=>{
 if(!r5Ready||!document.getElementById("r5-paid-confirm").checked)return;
 r5Ready=false;updateR5Button();
 const id=r5Select.value;
 try{
  const response=await fetch("/api/r5/submit",{method:"POST",headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},
   body:JSON.stringify({delivery_id:id,confirm_paid_sampled_review:true})});
  const result=await response.json();
  if(!response.ok){r5Output.textContent=result.error||(result.issues||[]).join("; ");return;}
  r5Output.textContent="审核运行中…";
  const poll=async()=>{
   try{
    const data=await fetch("/api/r5/paid-status").then(r=>r.json());
    r5Output.textContent="状态："+data.status+"\n"+JSON.stringify(data.result||{},null,2);
    if(data.status==="running"){setTimeout(poll,2000);}
    else {refreshR5();}
   }catch(e){r5Output.textContent=String(e);}
  };poll();
 }catch(e){r5Output.textContent=String(e);}
});
loadR5Deliveries();

const settingsOutput=document.getElementById("settings-output");
async function writeSettings(path,payload){
 const response=await fetch(path,{method:"POST",
   headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},
   body:JSON.stringify(payload)});
 const result=await response.json();
 if(!response.ok)throw Error(result.error||"无法保存");
 return result;
}
async function refreshSettings(){
 const s=await fetch("/api/settings").then(r=>r.json());
 document.getElementById("settings-r5-enabled").checked=s.r5_enabled;
 document.getElementById("proxy-mode").value=s.proxy_mode;
 document.getElementById("proxy-url").value=s.proxy_url;
 settingsOutput.textContent=s.deepseek_key_configured?"DeepSeek 密钥已配置（Keychain）":"DeepSeek 密钥尚未配置";
}
document.getElementById("save-settings").addEventListener("click",async()=>{
 try{
  const mode=document.getElementById("proxy-mode").value;
  await writeSettings("/api/settings",{
   r5_enabled:document.getElementById("settings-r5-enabled").checked,
   proxy_mode:mode,
   proxy_url:mode==="custom"?document.getElementById("proxy-url").value.trim():""
  });
  settingsOutput.textContent="设置已保存";r5Ready=false;updateR5Button();
 }catch(e){settingsOutput.textContent=String(e);}
});
document.getElementById("save-key").addEventListener("click",async()=>{
 const el=document.getElementById("deepseek-key");
 try{
  await writeSettings("/api/settings/key",{api_key:el.value});
  el.value="";await refreshSettings();
 }catch(e){el.value="";settingsOutput.textContent=String(e);}
});
document.getElementById("delete-key").addEventListener("click",async()=>{
 if(!confirm("确认删除 MG Studio 的 DeepSeek API Key？"))return;
 try{await writeSettings("/api/settings/key/delete",{});await refreshSettings();}
 catch(e){settingsOutput.textContent=String(e);}
});
refreshSettings().catch(e=>settingsOutput.textContent=String(e));

let reworkRuns=[];
const reworkSelect=document.getElementById("rework-run");
const reworkFindings=document.getElementById("rework-findings");
const reworkOutput=document.getElementById("rework-output");
async function loadReworkRuns(){
 try{
  const response=await fetch("/api/r5/rework-candidates");
  if(!response.ok)throw new Error("HTTP "+response.status);
  reworkRuns=(await response.json()).runs;
  reworkSelect.replaceChildren();
  for(const run of reworkRuns){
    const option=document.createElement("option");
    option.value=run.id;
    option.textContent=run.delivery_id+" · "+run.findings.length+" 项候选问题";
    reworkSelect.append(option);
  }
  if(!reworkRuns.length)reworkOutput.textContent="暂无有效的结构化返工候选";
  renderFindings();
 }catch(e){reworkOutput.textContent=String(e);}
}
function renderFindings(){
 reworkFindings.replaceChildren();
 document.getElementById("rework-confirm").checked=false;
 const run=reworkRuns.find(x=>x.id===reworkSelect.value);
 if(!run)return;
 const origin=document.createElement("p");
 origin.textContent="证据范围："+run.scope+" · 实现 SHA："+run.source_sha+" · 视频 SHA256："+run.video_sha256;
 reworkFindings.append(origin);
 for(const finding of run.findings){
   const box=document.createElement("div");box.className="item";
   const label=document.createElement("label");
   const choice=document.createElement("input");choice.type="checkbox";choice.className="rework-select";
   choice.value=finding.id;
   label.append(choice,document.createTextNode(" "+finding.id+" · "+finding.severity+" · "+(finding.timestamp_s??"时间未知")+"s"));
   const info=document.createElement("p");
   info.textContent="观察："+finding.observed+"\n证据："+finding.evidence+"\n预期："+finding.expected+"\n修复："+finding.fix_request;
   info.style.whiteSpace="pre-wrap";box.append(label,info);reworkFindings.append(box);
 }
}
reworkSelect.addEventListener("change",renderFindings);
document.getElementById("rework-refresh").addEventListener("click",loadReworkRuns);
document.getElementById("rework-dispatch").addEventListener("click",async()=>{
 const run=reworkRuns.find(x=>x.id===reworkSelect.value);
 const chosen=[...document.querySelectorAll(".rework-select:checked")].map(x=>x.value);
 if(!run||!chosen.length||!document.getElementById("rework-confirm").checked){
  reworkOutput.textContent="请核对证据、选择缺陷并勾选人工审批确认";return;
 }
 const files=document.getElementById("rework-allowed-files").value.split("\n").map(x=>x.trim()).filter(Boolean);
 const inbox=document.getElementById("rework-inbox-id").value.trim();
 if(!files.length||!inbox){reworkOutput.textContent="请填写允许修改的源码及新任务名称";return;}
 const button=document.getElementById("rework-dispatch");button.disabled=true;
 try{
   const response=await fetch("/api/r5/dispatch-rework",{method:"POST",
    headers:{"X-MG-CSRF":csrf,"Content-Type":"application/json"},
    body:JSON.stringify({run_id:run.id,selected_ids:chosen,allowed_files:files,
     inbox_id:inbox,confirm_rework_approval:true})});
   const result=await response.json();
   reworkOutput.textContent=response.ok?
     "任务已派发（尚未执行 R4）\n"+JSON.stringify(result,null,2):
     "BLOCKED · "+(result.error||JSON.stringify(result));
 }catch(e){reworkOutput.textContent=String(e);}
 finally{button.disabled=false;}
});
loadReworkRuns();
