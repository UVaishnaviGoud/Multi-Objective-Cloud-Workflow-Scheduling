document.addEventListener('DOMContentLoaded',()=>{
  const sidebar=document.getElementById('sidebar'),menu=document.getElementById('menuBtn');
  if(menu)menu.addEventListener('click',()=>sidebar.classList.toggle('open'));
  document.querySelectorAll('.tab-btn').forEach(btn=>btn.addEventListener('click',()=>{
    document.querySelectorAll('.tab-btn,.tab-panel').forEach(x=>x.classList.remove('active'));
    btn.classList.add('active');document.getElementById(btn.dataset.target).classList.add('active');
  }));
  const file=document.querySelector('input[type=file]');if(file)file.addEventListener('change',()=>{const name=document.getElementById('fileName');if(name)name.textContent=file.files[0]?.name||'No file selected'});
  renderDAG();renderResult();setTimeout(()=>document.querySelectorAll('.toast').forEach(t=>t.remove()),5500);
});

function renderDAG(){
  const canvas=document.getElementById('dagCanvas');if(!canvas)return;
  const tasks=JSON.parse(canvas.dataset.tasks),depth={},byId={};tasks.forEach(t=>byId[t.id]=t);
  const getDepth=id=>{if(depth[id]!==undefined)return depth[id];const d=byId[id].dependencies||[];return depth[id]=d.length?1+Math.max(...d.map(getDepth)):0};tasks.forEach(t=>getDepth(t.id));
  const groups={};tasks.forEach(t=>(groups[depth[t.id]]??=[]).push(t));const width=Math.max(canvas.clientWidth,520),height=Math.max(350,tasks.length*10+300);canvas.style.minWidth=width+'px';canvas.style.height=height+'px';
  const pos={};Object.entries(groups).forEach(([d,items])=>items.forEach((t,i)=>{pos[t.id]={x:35+(+d)*(width-120)/Math.max(Object.keys(groups).length-1,1),y:45+i*90+(height-items.length*90)/2}}));
  tasks.forEach(t=>(t.dependencies||[]).forEach(dep=>{const a=pos[dep],b=pos[t.id],dx=b.x-a.x,dy=b.y-a.y,len=Math.sqrt(dx*dx+dy*dy),line=document.createElement('div');line.className='dag-line';line.style.cssText=`left:${a.x+27}px;top:${a.y+27}px;width:${len}px;transform:rotate(${Math.atan2(dy,dx)}rad)`;canvas.appendChild(line)}));
  tasks.forEach(t=>{const n=document.createElement('div');n.className='dag-node';n.textContent=t.id;n.style.left=pos[t.id].x+'px';n.style.top=pos[t.id].y+'px';canvas.appendChild(n)});
}

function renderResult(){
  if(!window.RESULT_DATA)return;const data=window.RESULT_DATA.algorithms,labels=Object.keys(data).map(k=>({fcfs:'FCFS',min_min:'Min-Min',heft:'HEFT',proposed:'GNN–DRL'})[k]);
  const canvas=document.getElementById('comparisonChart');if(canvas&&window.Chart)new Chart(canvas,{type:'bar',data:{labels,datasets:[{label:'Makespan',data:Object.values(data).map(x=>x.metrics.makespan),backgroundColor:['#b8b1d8','#8fc9ee','#ffb889','#7657ff'],borderRadius:8},{label:'Cost',data:Object.values(data).map(x=>x.metrics.total_cost),backgroundColor:['#e1ddf3','#c8e6f8','#ffd9bf','#ff6f9e'],borderRadius:8}]},options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{position:'bottom',labels:{boxWidth:10,usePointStyle:true}}},scales:{x:{grid:{display:false}},y:{grid:{color:'#eef0f5'},beginAtZero:true}}}});
  const gantt=document.getElementById('gantt');if(gantt){const schedule=JSON.parse(gantt.dataset.schedule),max=+gantt.dataset.makespan;[...new Set(schedule.map(x=>x.resource))].forEach(r=>{const row=document.createElement('div');row.className='gantt-row';row.innerHTML=`<label>${r}</label>`;schedule.filter(x=>x.resource===r).forEach(x=>{const bar=document.createElement('div');bar.className='gantt-bar';bar.style.left=(x.start/max*100)+'%';bar.style.width=Math.max(x.duration/max*100,4)+'%';bar.textContent=x.task;row.appendChild(bar)});gantt.appendChild(row)})}
}

