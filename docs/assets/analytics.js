(() => {
  'use strict';
  const R=window.RESULTS,E=window.EXTENSIONS,$=s=>document.querySelector(s);
  const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const pct=v=>v==null?'n/a':`${(v*100).toFixed(1)}%`, dec=v=>v==null?'n/a':v.toFixed(3);
  const interval=(v,f=pct)=>v?`${f(v[0])} (${f(v[1])}–${f(v[2])})`:'n/a';
  const colours=['var(--rule)','var(--pca)','var(--pca)','var(--iforest)','var(--iforest)','var(--pca)','var(--ink)'];
  // Explicit palette values fall back to the journal's detector families.
  const colour=i=>['#397bad','#b96d25','#b96d25','#32806d','#32806d','#b96d25','var(--ink)'][i];
  function table(target,caption,headers,rows){
    $(target).innerHTML=`<table class="booktabs"><caption class="sr-only">${esc(caption)}</caption><thead><tr>${headers.map(h=>`<th scope="col">${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(row=>`<tr>${row.map((v,i)=>i?`<td>${esc(v)}</td>`:`<th scope="row">${esc(v)}</th>`).join('')}</tr>`).join('')}</tbody></table>`;
  }
  let current=[];
  function selection(){return{condition:$('#training').value,test:$('#pattern').value,size:Number($('#size').value)};}
  function svg(target,label,rows,auc=false){
    const width=Math.max(290,Math.round($(target).clientWidth)),left=8,right=auc?25:62,plot=width-left-right,h=rows.length*66+38;
    let body='';
    for(const v of [0,.25,.5,.75,1]){const x=left+v*plot;body+=`<line class="axis" x1="${x}" y1="22" x2="${x}" y2="${h-22}" ${auc&&v===.5?'style="stroke:var(--ink-3);stroke-dasharray:3 4"':''}/><text x="${x}" y="${h-4}" text-anchor="${v===0?'start':v===1?'end':'middle'}">${auc?v.toFixed(2):`${v*100}%`}</text>`;}
    rows.forEach((row,i)=>{
      const y=i*66+15,c=colour(i);body+=`<text class="chart-row-label" x="8" y="${y}">${esc(row.name)}</text>`;
      if(auc){const v=row.a;if(!v)return;const x=left+v[0]*plot,lo=left+v[1]*plot,hi=left+v[2]*plot;body+=`<g><title>${esc(row.name)}: ${interval(v,dec)}</title><line x1="${lo}" y1="${y+23}" x2="${hi}" y2="${y+23}" stroke="${c}" stroke-width="2"/><path d="M${lo} ${y+18}v10 M${hi} ${y+18}v10" stroke="${c}"/><circle cx="${x}" cy="${y+23}" r="4" fill="${c}"/></g>`;}
      else{[row.a,row.b].forEach((v,k)=>{const cy=y+8+k*16;body+=`<g><title>${esc(row.name)} — ${k?row.bLabel:row.aLabel}: ${interval(v)}</title><rect x="${left}" y="${cy}" width="${Math.max(0,v[0]*plot)}" height="10" fill="${k?'none':c}" stroke="${c}" stroke-width="${k?1.3:0}"/><text x="${left+plot+8}" y="${cy+9}">${pct(v[0])}</text></g>`;});}
    });
    $(target).innerHTML=`<svg role="img" aria-label="${esc(label)}. Exact values in the table below." viewBox="0 0 ${width} ${h}"><title>${esc(label)}</title>${body}</svg>`;
  }
  function render(){
    const{condition,test,size}=selection(),i=R.sizes.indexOf(size);
    current=R.detectors.map(name=>({name,caught:R.catch[condition][test][name][i],honest:R.catch[condition].control_calm[name][i],auc:R.auc[condition][`${test}|genuine`][name][i],calm:R.fpr[condition][name].calm,volatile:R.fpr[condition][name].volatile}));
    svg('[data-analytics-chart="catch"]','Spoofs caught and honest orders flagged',current.map(r=>({name:r.name,a:r.caught,b:r.honest,aLabel:'Spoofs caught',bLabel:'Honest orders flagged'})));
    svg('[data-analytics-chart="auc"]','AUC: spoofs versus honest large orders',current.map(r=>({name:r.name,a:r.auc})),true);
    svg('[data-analytics-chart="fpr"]','False alarms on ordinary calm and volatile bars',current.map(r=>({name:r.name,a:r.calm,b:r.volatile,aLabel:'Calm market',bLabel:'Volatile market'})));
    $('[data-sample]').textContent=`Calm-market evaluation · ${size}× typical order size · ${current[0].caught[3]} spoof episodes and ${current[0].honest[3]} honest-order episodes per detector.`;
    const rule=current[0],lstm=current.find(r=>r.name.startsWith('LSTM'));
    $('[data-analytics-reading]').textContent=`At this setting, the rule catches ${pct(rule.caught[0])} of spoofs and flags ${pct(rule.honest[0])} of honest orders. The LSTM’s AUC is ${dec(lstm.auc[0])} against honest orders of the same size. Compare both detection and false accusations before judging performance.`;
    table('[data-comparison-table]','Selected detector results',['Detector','Spoofs caught (95% CI)','Honest flagged (95% CI)','AUC (95% CI)','Calm false alarms (95% CI)','Volatile false alarms (95% CI)','Spoof episodes','Honest episodes'],current.map(r=>[r.name,interval(r.caught),interval(r.honest),interval(r.auc,dec),interval(r.calm),interval(r.volatile),r.caught[3],r.honest[3]]));
    const impact=R.impact[test==='layer_calm'?'layered':'single wall'].find(r=>r.size===size),g=impact.fill_gain;
    const pp=v=>`${v>=0?'+':''}${(v*100).toFixed(1)}`;
    $('[data-impact]').innerHTML=`<p class="impact-value">${pp(g[0])} points</p><p class="impact-ci">95% CI: ${pp(g[1])} to ${pp(g[2])} percentage points<br>${impact.n} paired sessions</p><div class="impact-pair"><div><strong>${pct(impact.fill_wall)}</strong><span>Filled with the fake wall</span></div><div><strong>${pct(impact.fill_honest)}</strong><span>Filled without it</span></div></div>`;
  }
  if(!R||!E){$('[data-analytics-reading]').textContent='The results could not load. Reload the page to try again.';return;}
  $('[data-analytics-generated]').textContent=`Data export · ${R.generated}`;
  table('[data-robustness-table]','Claims across simulated markets',['Claim',...E.markets],E.checks.map(r=>[r.claim,...E.markets.map(m=>r[m]) ]));
  table('[data-order-table]','Individual order Isolation Forest',['Features','Order size','Spoofs flagged','Honest flagged','AUC versus honest (95% CI)','Spoof orders','Honest orders'],E.orders.map(r=>[r.variant,`${r.size_mult}×`,pct(r.spoof_walls_flagged),pct(r.genuine_flagged),interval([r.auc_spoof_vs_genuine,r.ci_low,r.ci_high],dec),r.n_spoof,r.n_genuine]));
  table('[data-resolution-table]','One-step resolution, 16× orders',['Detector','Single-wall caught','Layered caught','Honest flagged','AUC versus honest','Normal false alarms'],E.resolution.map(r=>[r.detector,pct(r.spoofs_caught_16),pct(r.layered_caught_16),pct(r.genuine_flagged_16),dec(r.auc_spoof_vs_genuine_16),pct(r.false_alarm_rate)]));
  $('.analytics-filters').addEventListener('change',render);
  $('.analytics-filters').addEventListener('reset',()=>setTimeout(render,0));
  $('#download-comparison').addEventListener('click',()=>{
    const{condition,test,size}=selection();
    const headings=['condition','test','size_mult','detector',...['catch','honest_flag','auc_vs_genuine','fpr_calm','fpr_volatile'].flatMap(k=>[k,`${k}_ci_low`,`${k}_ci_high`]),'n_spoof','n_honest','n_calm_sessions','n_volatile_sessions'];
    const rows=current.map(r=>[condition,test,size,r.name,...[r.caught,r.honest,r.auc,r.calm,r.volatile].flatMap(v=>v.slice(0,3)),r.caught[3],r.honest[3],r.calm[3],r.volatile[3]]);
    const csv=[headings,...rows].map(r=>r.map(v=>`"${String(v).replaceAll('"','""')}"`).join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=`detectors-${condition}-${test}-${size}x.csv`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  });
  $('#analytics-theme').addEventListener('click',()=>{const dark=document.documentElement.dataset.theme==='dark'||(!document.documentElement.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);const theme=dark?'light':'dark';document.documentElement.dataset.theme=theme;try{localStorage.setItem('dtu-theme',theme);}catch(_){}dispatchEvent(new Event('themechange'));});
  let resizeTimer;addEventListener('resize',()=>{clearTimeout(resizeTimer);resizeTimer=setTimeout(render,100);});render();
})();

