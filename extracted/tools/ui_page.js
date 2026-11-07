const $=i=>document.getElementById(i),log=$('log');let last='',fileMode=false;const DEFPH=$('in').placeholder;
function add(t,c){const d=document.createElement('div');d.className='b '+c;d.textContent=t;log.appendChild(d);log.scrollTop=log.scrollHeight;if(c=='n')last=t;return d}
const note=t=>add(t,'s');   // an interface notice (not the model speaking): muted style, never saved as «the last reply»
/*ZIP-START*/
const CRC=(()=>{const t=new Uint32Array(256);for(let n=0;n<256;n++){let c=n;for(let k=0;k<8;k++)c=c&1?0xEDB88320^(c>>>1):c>>>1;t[n]=c>>>0}return t})();
function crc32(b){let c=0xFFFFFFFF;for(let i=0;i<b.length;i++)c=CRC[(c^b[i])&255]^(c>>>8);return(c^0xFFFFFFFF)>>>0}
function makeZip(files){const enc=new TextEncoder(),parts=[],cd=[];let off=0;
 const u16=v=>[v&255,(v>>8)&255],u32=v=>[v&255,(v>>8)&255,(v>>16)&255,(v>>>24)&255];
 for(const f of files){const nb=enc.encode(f.name),db=enc.encode(f.body),crc=crc32(db);
  const lh=new Uint8Array([0x50,0x4b,3,4,...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0x21),...u32(crc),...u32(db.length),...u32(db.length),...u16(nb.length),...u16(0)]);
  parts.push(lh,nb,db);
  cd.push(new Uint8Array([0x50,0x4b,1,2,...u16(20),...u16(20),...u16(0x0800),...u16(0),...u16(0),...u16(0x21),...u32(crc),...u32(db.length),...u32(db.length),...u16(nb.length),...u16(0),...u16(0),...u16(0),...u16(0),...u32(0),...u32(off)]),nb);
  off+=lh.length+nb.length+db.length}
 let cdl=0;for(const c of cd)cdl+=c.length;
 const end=new Uint8Array([0x50,0x4b,5,6,...u16(0),...u16(0),...u16(files.length),...u16(files.length),...u32(cdl),...u32(off),...u16(0)]);
 return new Blob([...parts,...cd,end],{type:'application/zip'})}
/*ZIP-END*/
function download(blob,name){const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(a.href),8000)}
/* ---- the file button: gray = no file is ever made from the chat; blue = every message describes a file to make ---- */
function showFileResult(r){
 if(r.text)add(r.text,'n');
 if(!r.files.length){note('ما قدرت أكتب ملفا واضحا لهذا الوصف. جرّب وصفا أدق: النوع، الاسم، وماذا فيه. مثلا: أنشئ ملف نصي فيه قائمة مشتريات: خبز، حليب باسم list.txt');return}
 let blob,name;
 if(r.files.length==1){const f=r.files[0];blob=new Blob([f.body],{type:'text/plain;charset=utf-8'});name=f.name.split('/').pop()}
 else{blob=makeZip(r.files);name=(r.files[0].name.includes('/')?r.files[0].name.split('/')[0]:'nuwaa_project')+'.zip'}
 const d=note('✅ جهزت '+(r.files.length==1?'الملف':'المشروع ('+r.files.length+' ملفات في zip واحد)')+' فعلا: '+name+' ('+blob.size+' بايت) وبدأ التنزيل، وإن لم ينزل اضغط الزر. لم أشغّل الكود، راجعه قبل الاعتماد عليه.');
 const b=document.createElement('button');b.className='dl';b.textContent='⬇ تنزيل '+name;b.onclick=()=>download(blob,name);d.appendChild(document.createElement('br'));d.appendChild(b);
 try{download(blob,name)}catch(e){}}
$('fbtn').onclick=()=>{fileMode=!fileMode;$('fbtn').classList.toggle('on',fileMode);$('mbar').classList.toggle('on',fileMode);$('in').placeholder=fileMode?'صف الملف: النوع، الاسم، وماذا فيه...':DEFPH};
function send(){const t=$('in').value.trim();if(!t)return;$('in').value='';add(t,'u');
 if(fileMode){const w=note('… النموذج يكتب الملف بنفسه، قد يأخذ نصف دقيقة');setTimeout(()=>{let r;try{r=E.respondFile(t)}catch(e){r={text:'خطأ: '+e.message,files:[]}}w.remove();showFileResult(r)},40)}
 else add(E.respond(t),'n')}
function tab(i){for(let k=0;k<4;k++){$('s'+k).classList.toggle('on',k==i);$('t'+k).classList.toggle('on',k==i)}if(i==2)renderMem();if(i==3)$('hwinfo').textContent=hw()}
function renderMem(){const m=$('mem');m.innerHTML='';const c=document.createElement('div');c.className='card';c.textContent='جمل سمعتها ('+E.count()+')';m.appendChild(c);
 const box=document.createElement('div');box.className='card';
 for(const h of E.memory().slice(-40)){const r=document.createElement('div');r.className='row';r.textContent=h;box.appendChild(r)}m.appendChild(box)}
$('go').onclick=send;$('in').addEventListener('keydown',e=>{if(e.key=='Enter'&&!e.shiftKey){e.preventDefault();send()}});
for(let k=0;k<4;k++)$('t'+k).onclick=()=>tab(k);
$('plus').onclick=e=>{e.stopPropagation();$('pm').style.display=$('pm').style.display=='block'?'none':'block'};document.addEventListener('click',()=>$('pm').style.display='none');
$('pSend').onclick=()=>$('file').click();
$('file').onchange=async e=>{const f=e.target.files[0];if(!f)return;const t=(await f.text()).slice(0,300000);add('📎 '+f.name,'u');add(E.respond(t.split('\n').slice(0,200).join('\n')),'n');e.target.value=''};
$('pMake').onclick=()=>{const t=$('in').value.trim()||last;if(!t){alert('اكتب النص في الخانة أولا أو اسألني ثم اضغط ＋');return}
 const n=prompt('اسم الملف','nuwaa.txt')||'nuwaa.txt';download(new Blob([t],{type:'text/plain;charset=utf-8'}),n)};
$('dev').onclick=()=>{const r=E.develop(),p=$('rep');p.style.display='block';
 p.textContent='راجعت ما سمعته منك: '+r.messages+' رسالة.\n• جودتي على آخر كلامك: '+r.bits.toFixed(2)+' بت/حرف (الأقل أفضل).\n• حجمي: '+r.params+' معامل.\nلتدريب الأوزان فعلا افتح تبويب ⚡ رفع الفهم.'};
$('pNew').onclick=()=>{E.newChat();log.innerHTML='';note('محادثة جديدة. انتهت الذاكرة القصيرة للمحادثة السابقة.')};
/* ---- raise understanding: training in a background worker, at the CPU share the user picks ---- */
let worker=null,running=false,reloadAfter=false,corpusLen=1e5,nextReview=120,rv={pass:0,total:0,learned:0};
function hw(){let gpu='غير معروف';try{const c=document.createElement('canvas'),gl=c.getContext('webgl'),x=gl.getExtension('WEBGL_debug_renderer_info');gpu=x?gl.getParameter(x.UNMASKED_RENDERER_WEBGL):gl.getParameter(gl.RENDERER)}catch(e){}
 return 'جهازك: '+(navigator.hardwareConcurrency||'؟')+' نواة · ذاكرة تقريبية '+(navigator.deviceMemory?navigator.deviceMemory+' GB':'؟')+' · كرت الشاشة: '+gpu+'\nالتدريب هنا يستخدم نواة معالج واحدة فقط، ولا يستخدم كرت الشاشة. للتدريب الكبير على كرت الشاشة استعمل Colab (دفتر tools/Nuwaa_40m_colab.ipynb).'}
function idb(){return new Promise((res,rej)=>{const r=indexedDB.open('nuwaa-weights',1);r.onupgradeneeded=()=>r.result.createObjectStore('w');r.onsuccess=()=>res(r.result);r.onerror=()=>rej(r.error)})}
async function saveW(P){try{const db=await idb(),tx=db.transaction('w','readwrite');tx.objectStore('w').put(P,'P');await new Promise(r=>tx.oncomplete=r)}catch(e){}}
async function loadW(){try{const db=await idb();return await new Promise(res=>{const q=db.transaction('w').objectStore('w').get('P');q.onsuccess=()=>res(q.result);q.onerror=()=>res(null)})}catch(e){return null}}
async function clearW(){try{const db=await idb(),tx=db.transaction('w','readwrite');tx.objectStore('w').delete('P');await new Promise(r=>tx.oncomplete=r)}catch(e){}}
loadW().then(w=>{if(w&&w.PE&&w.PE.length==E.params().PE.length){E.setParams(w);$('tnote').textContent='✅ حمّلت تدريبك المحفوظ من المرة السابقة.'}});
const ITEMS=['خبز','حليب','بيض','تمر','قهوة','شاي','رز','جبن','عسل','ماء','تفاح','موز','لبن','زيت','ملح','سكر'];
function selfTask(){const k=3+Math.floor(Math.random()*3),pick=[...ITEMS].sort(()=>Math.random()-.5).slice(0,k),name='t'+(100+Math.floor(Math.random()*900))+'.txt';return{ask:'أنشئ ملف نصي فيه قائمة مشتريات: '+pick.join('، ')+' باسم '+name,name,body:pick.join('\n')}}
function selfReview(){let n=0;const one=()=>{if(!running||n>=3)return;n++;const t=selfTask(),r=E.respondFile(t.ask);rv.total++;
  if(r.files.length&&r.files[0].name==t.name&&r.files[0].body.trim()==t.body){rv.pass++;rv.learned++;worker.postMessage({type:'extra',text:'س:'+t.ask+'\nج:'+r.raw.replace(/\n/g,'¶')+'\n'})}setTimeout(one,200)};one()}
function showProg(m){const pct=+$('pct').value,wpp=corpusLen/100,eta=Math.max(0,(wpp-m.steps))*m.stepMs*100/pct/1000;
 $('trep').textContent='⚡ شغّال\n\n• الخطوات: '+m.steps+' (كل خطوة ~100 حرف)\n• خطأ التدريب الحالي: '+m.loss.toFixed(3)+' بت/حرف\n• قياسي على نص ثابت لم أتدرب عليه: '+m.startHeld.toFixed(3)+' ← '+m.held.toFixed(3)+' (الأقل أفضل)\n• رجوع للأفضل لما ساء القياس: '+m.rollbacks+' مرة\n'
  +($('sr').checked?'• مراجعتي لنفسي (مهام ملفات أعرف جوابها): نجحت في '+rv.pass+' من '+rv.total+'، وتعلمت من '+rv.learned+' جواب صحيح لي\n':'')
  +'• سرعة الخطوة: '+Math.round(m.stepMs)+' ملّي ثانية شغل، وبالاستهلاك المختار ~'+(m.stepMs*100/pct/1000).toFixed(1)+' ثانية للخطوة\n• تقدير مرور واحد على كل بياناتي: '+(eta>3600?Math.round(eta/3600)+' ساعة تقريبا':Math.round(eta/60)+' دقيقة تقريبا')
  +'\n\nالتدريب يبقى شغالا في الخلفية وتقدر تكلمني. يقف إذا أغلقت الصفحة.';
 if(m.steps>=nextReview&&$('sr').checked){nextReview=m.steps+120;setTimeout(selfReview,50)}}
function setTrainUI(on){$('tgo').disabled=false;$('tgo').textContent=on?'⏹ إيقاف (يحفظ الأفضل)':'⚡ ابدأ رفع الفهم'}
async function startTrain(){
 if(!window.Worker||!window.DecompressionStream||!window.indexedDB){alert('متصفحك لا يدعم التدريب هنا (يحتاج Worker وDecompressionStream). جرّب Chrome أو Edge حديثا.');return}
 $('tgo').disabled=true;$('trep').style.display='block';$('trep').textContent='أجهّز بيانات التدريب...';
 try{const b64=$('corpusgz').textContent.match(/[A-Za-z0-9+\/=]{100,}/)[0],bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
  const corpus=await new Response(new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip'))).text();corpusLen=corpus.length;nextReview=120;rv={pass:0,total:0,learned:0};
  worker=new Worker(URL.createObjectURL(new Blob([$('trainsrc').textContent],{type:'text/javascript'})));
  worker.onmessage=e=>{const m=e.data;
   if(m.type==='ready'){running=true;worker.postMessage({type:'start',pct:+$('pct').value});setTrainUI(true);$('trep').textContent='بدأت. قياسي الأولي: '+m.held.toFixed(3)+' بت/حرف على '+m.pairs+' زوج تدريب...'}
   else if(m.type==='progress')showProg(m);
   else if(m.type==='weights'){E.setParams(m.P);saveW(m.P)}
   else if(m.type==='stopped'){E.setParams(m.P);saveW(m.P);running=false;setTrainUI(false);worker.terminate();worker=null;$('trep').textContent+='\n\n⏹ توقفت وحفظت أفضل حالة. القياس: '+m.startHeld.toFixed(3)+' ← '+m.held.toFixed(3)+' بت/حرف (الأقل أفضل).';if(reloadAfter)location.reload()}};
  worker.onerror=e=>{$('trep').textContent='خطأ في التدريب: '+(e.message||'غير معروف');running=false;setTrainUI(false)};
  worker.postMessage({type:'init',P:E.params(),D:E.dims(),chars:E.chars,corpus})
 }catch(e){$('trep').textContent='ما قدرت أبدأ: '+e.message;$('tgo').disabled=false}}
$('tgo').onclick=()=>{if(running){$('tgo').disabled=true;worker.postMessage({type:'stop'})}else startTrain()};
$('pct').oninput=()=>{$('plab').textContent='الاستهلاك: '+$('pct').value+'% من نواة معالج واحدة';if(worker&&running)worker.postMessage({type:'pct',pct:+$('pct').value})};
for(const b of document.querySelectorAll('[data-p]'))b.onclick=()=>{$('pct').value=b.dataset.p;$('pct').oninput()};
$('trel').onclick=()=>{if(running){reloadAfter=true;$('tgo').click()}else location.reload()};
$('trst').onclick=async()=>{if(confirm('أرجع للنموذج الأصلي وأمسح تدريبي المحفوظ في هذا المتصفح؟')){await clearW();location.reload()}};
note('نواة: نموذج يكتب كل ردوده حرفا بعد حرف، بلا ردود جاهزة. هذه السطور المنقّطة رسائل من الواجهة، وليست كلام النموذج. لإنشاء ملف اضغط 📄 (يصير أزرق) ثم صف الملف. لتدريبه اضغط ⚡ رفع الفهم.');
