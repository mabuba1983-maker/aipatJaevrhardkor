/*ENGINE-START* Local engine: the Nuwaa recurrent language model (GRU), mirror of nuwaa/lm/gru.py. No network, no key, no canned phrases. */
const E=(()=>{
const B64="__WEIGHTS_B64__";
const f16=h=>{const s=(h&0x8000)?-1:1,e=(h>>10)&31,f=h&1023;if(e==0)return s*Math.pow(2,-14)*(f/1024);if(e==31)return f?NaN:s*Infinity;return s*Math.pow(2,e-15)*(1+f/1024)};
const raw=Uint8Array.from(atob(B64),c=>c.charCodeAt(0)),dv=new DataView(raw.buffer);
const Em=dv.getInt32(4,true),H=dv.getInt32(8,true),V=dv.getInt32(12,true),nj=dv.getInt32(16,true);
const chars=JSON.parse(new TextDecoder().decode(raw.slice(20,20+nj)));let off=20+nj;
const take=n=>{const a=new Float32Array(n);for(let i=0;i<n;i++){a[i]=f16(dv.getUint16(off,true));off+=2}return a};
const H3=3*H,PE=take(V*Em),Wx1=take(Em*H3),Wh1=take(H*H3),b1=take(H3),Wx2=take(H*H3),Wh2=take(H*H3),b2=take(H3),Wo=take(H*V),bo=take(V);
const vocab=new Map(chars.map((c,i)=>[c,i])),cid=c=>vocab.has(c)?vocab.get(c):1,NL=cid('\n');
const sg=x=>1/(1+Math.exp(-x));
function cell(gx,hp,Wh){const tmp=new Float32Array(2*H);for(let j=0;j<2*H;j++)tmp[j]=gx[j];
 for(let q=0;q<H;q++){const hv=hp[q];if(hv===0)continue;const o=q*H3;for(let j=0;j<2*H;j++)tmp[j]+=hv*Wh[o+j]}
 const z=new Float32Array(H),rh=new Float32Array(H),an=new Float32Array(H),out=new Float32Array(H);
 for(let j=0;j<H;j++){const r=sg(tmp[j]);z[j]=sg(tmp[H+j]);rh[j]=r*hp[j];an[j]=gx[2*H+j]}
 for(let q=0;q<H;q++){const v=rh[q];if(v===0)continue;const o=q*H3+2*H;for(let j=0;j<H;j++)an[j]+=v*Wh[o+j]}
 for(let j=0;j<H;j++)out[j]=(1-z[j])*hp[j]+z[j]*Math.tanh(an[j]);return out}
function step(id,st){const g1=new Float32Array(H3);for(let j=0;j<H3;j++)g1[j]=b1[j];
 for(let q=0;q<Em;q++){const ev=PE[id*Em+q],o=q*H3;for(let j=0;j<H3;j++)g1[j]+=ev*Wx1[o+j]}
 st[0]=cell(g1,st[0],Wh1);const g2=new Float32Array(H3);for(let j=0;j<H3;j++)g2[j]=b2[j];
 for(let q=0;q<H;q++){const hv=st[0][q];if(hv===0)continue;const o=q*H3;for(let j=0;j<H3;j++)g2[j]+=hv*Wx2[o+j]}
 st[1]=cell(g2,st[1],Wh2);const p=new Float32Array(V);for(let j=0;j<V;j++)p[j]=bo[j];
 for(let q=0;q<H;q++){const hv=st[1][q];if(hv===0)continue;const o=q*V;for(let j=0;j<V;j++)p[j]+=hv*Wo[o+j]}
 let mx=-1e30;for(let j=0;j<V;j++)if(p[j]>mx)mx=p[j];let s=0;for(let j=0;j<V;j++){p[j]=Math.exp(p[j]-mx);s+=p[j]}for(let j=0;j<V;j++)p[j]/=s;return p}
class Mem{constructor(){this.t=new Map();this.n=0}
 add(text){const s='\n'+text+'\n';for(let i=1;i<s.length;i++)for(let o=1;o<=8&&i-o>=0;o++){const k=s.slice(i-o,i);let m=this.t.get(k);if(!m){m=new Map();this.t.set(k,m)}m.set(s[i],(m.get(s[i])||0)+1)}this.n+=s.length}
 dist(ctx,minO=1){for(let o=Math.min(8,ctx.length);o>=minO;o--){const c=this.t.get(ctx.slice(ctx.length-o));if(c)return[o,c]}return null}}
const long=new Mem();let memory=[];
try{memory=JSON.parse(localStorage.getItem('nuwaa.mem2')||'[]')}catch(e){}for(const l of memory)long.add(l);
const saveMem=()=>{try{localStorage.setItem('nuwaa.mem2',JSON.stringify(memory.slice(-500)))}catch(e){}};
class Session{constructor(){this.st=[new Float32Array(H),new Float32Array(H)];this.p=null;this.text='';this.short=new Mem();this.replies=[];this.feed('\n')}
 feed(s){for(const ch of s){this.p=step(cid(ch),this.st);this.text+=ch}}
 mix(p0,useMem=true){let p=Float32Array.from(p0);if(!useMem)return p;const ctx=this.text.slice(-8);
  for(const mem of [long,this.short]){const d=mem.dist(ctx,4);if(!d)continue;const[o,cnt]=d;let tot=0;for(const c of cnt.values())tot+=c;
   const lam=.6*tot/(tot+.1)*Math.min(1,(o-3)/4),q=new Float32Array(V);for(const[ch,k]of cnt)q[cid(ch)]+=k/tot;for(let j=0;j<V;j++)p[j]=(1-lam)*p[j]+lam*q[j]}return p}
 reply(user,maxChars=400,opts={}){const u=user.replace(/\n/g,' ¶ ').trim();this.feed('س:'+u+'\nج:');let out='';const nq=u.split(/\s+/).join(' ');const same=this.replies.some(r=>r[0]==nq);const prev=new Set();if(!same)for(const r of this.replies.slice(-6))for(let k=0;k+8<=r[1].length;k++)prev.add(r[1].slice(k,k+8));const selfG=new Set();const src=copySource(u),cst={p:null};
  for(let i=0;i<maxChars;i++){const p=this.mix(this.p,opts.mem!==false);p[0]=0;
   const cc=opts.copy===false?null:copyDist(src,out,cst);if(cc){const q=new Float32Array(V);q[cid(cc==='\n'?'¶':cc)]=1;for(let j=0;j<V;j++)p[j]=.1*p[j]+.9*q[j]}
   const fileMode=out.includes('<<ملف:'),openBlk=out.lastIndexOf('<<ملف:')>out.lastIndexOf('<<نهاية>>');if(out.length<3||openBlk)p[NL]=0;{let s0=0;for(let j=0;j<V;j++)s0+=p[j];if(s0<=0)p[NL]=1}
   if(!fileMode&&out.length>=7){const tail=out.slice(-9);let any=false;for(let j=0;j<V;j++){if(p[j]<=0||j==NL){if(p[j]>0)any=true;continue}const c=tail+chars[j];if((c.length>=10&&selfG.has(c.slice(-10)))||(c.length>=8&&prev.has(c.slice(-8))))p[j]=0;else any=true}if(!any){p.fill(0);p[NL]=1}}let mx=0,best=1;for(let j=0;j<V;j++)if(p[j]>mx){mx=p[j];best=j}
   for(let j=0;j<V;j++)if(p[j]<.15*mx)p[j]=0;for(let j=0;j<V;j++)if(p[j]>0)p[j]=Math.pow(p[j],1/.7);
   const sd=Float32Array.from(p).sort(),cut=sd[V-8];for(let j=0;j<V;j++)if(p[j]<cut)p[j]=0;
   let s=0;for(let j=0;j<V;j++)s+=p[j];let pick=best;if(s>0){let r=Math.random()*s;for(let j=0;j<V;j++){r-=p[j];if(r<=0&&p[j]>0){pick=j;break}}}
   this.p=step(pick,this.st);const ch=chars[pick];this.text+=ch;if(ch=='\n')break;out+=ch;if(out.length>=10)selfG.add(out.slice(-10));
   if(!fileMode&&out.length>=48&&out.slice(0,-24).includes(out.slice(-24))){out=out.slice(0,-24);break}}
  out=out.replace(/¶/g,'\n');if(!out.includes('<<ملف:')){const seen=new Set(),parts=out.split(/(?<=[.!?؟\n])/),keep=[];for(const x of parts){const k=x.trim();if(k.length>=6&&seen.has(k))continue;seen.add(k);keep.push(x)}out=keep.join('')}out=out.trim();this.replies.push([nq,out]);if(this.replies.length>12)this.replies.shift();this.short.add('س:'+u);return out}}
/* ---- files the MODEL builds: <<ملف:folder/name.ext>> ... <<نهاية>> (same rules as FileTools.kt / gru.py) ---- */
const OKEXT=new Set(['txt','md','csv','json','html','css','js','py','kt','java','sql','sh','xml']);
function copySource(u){return u.replace(/\s*،\s*/g,'\n').replace(/باسم /g,'\x01ملف:').replace(/مجلد /g,'\x01ملف:').replace(/(\x01ملف:)+/g,'\x01ملف:')}
function listFile(o){const i=o.lastIndexOf('\x01ملف:'),j=o.indexOf('>>',i);return i>=0&&j>i&&/\.(txt|md)$/.test(o.slice(i+5,j).trim().toLowerCase())}
function copyDist(src,out,st){
 if(out.lastIndexOf('<<ملف:')<=out.lastIndexOf('<<نهاية>>')){st.p=null;return null}
 const o=out.replace(/¶/g,'\n').replace(/<<ملف:/g,'\x01ملف:');let p=st.p;
 if(p!==null&&(p>=src.length||p==0||o.slice(-1)!==src[p-1]))p=null;
 if(p===null){
  if(o.endsWith('\x01ملف:')){const k=src.indexOf('\x01ملف:');p=k>=0?k+5:null}
  else if(o.endsWith('= [')&&src.includes('['))p=src.indexOf('[')+1;
  else if(o.endsWith('>>\n')&&src.includes(': ')&&listFile(o))p=src.indexOf(': ')+2;
  else{for(let L=Math.min(12,o.length);L>=3;L--){const pos=src.indexOf(o.slice(-L));if(pos>=0){p=pos+L;break}}}}
 if(p===null||p>=src.length){st.p=null;return null}
 const ch=src[p];if(ch==='\x01'||(ch===' '&&o.slice(-1)!==',')){st.p=null;return null}
 st.p=p+1;return ch}
function cleanName(raw){let n=raw.trim().split('/').pop().replace(/[^\p{L}\p{N}_\-. ]/gu,'').trim().replace(/ /g,'_').replace(/^\.+/,'');const ext=n.split('.').length>1?n.split('.').pop().toLowerCase():'';return(n.length<3||n.length>60||!OKEXT.has(ext))?null:n}
function cleanPath(raw){const parts=raw.trim().replace(/\\/g,'/').split('/').filter(x=>x.trim());if(!parts.length||parts.length>2)return null;const f=cleanName(parts[parts.length-1]);if(!f)return null;if(parts.length==1)return f;const d=parts[0].replace(/[^\p{L}\p{N}_\-]/gu,'').slice(0,40);return d?d+'/'+f:null}
function fileBlocks(text){const files=[];let total=0;const re=/<<ملف:([^>\n]{1,80})>>\n?([\s\S]*?)\n?<<نهاية>>/g;let m;
 while((m=re.exec(text))){const name=cleanPath(m[1]);if(!name||!m[2].trim()||m[2].length>20000)continue;total+=m[2].length;if(files.length>=12||total>60000)break;if(files.some(f=>f.name==name))continue;files.push({name,body:m[2].replace(/\n+$/,'')+'\n'})}return files}
function showBlocks(text){return text.replace(/<<ملف:([^>\n]{1,80})>>\n?([\s\S]*?)\n?<<نهاية>>/g,(a,n,b)=>'```\n'+b.replace(/\n+$/,'')+'\n```')}
function respondFile(q){q=q.trim();const s=new Session();const r=s.reply(q,1500,{mem:false,copy:true});return{text:showBlocks(r),files:fileBlocks(r),raw:r}}
let sess=new Session();
function hear(q){const l=q.replace(/\n/g,' ').trim();if(!l)return;memory.push(l);long.add(l);saveMem()}
function respond(q){q=q.trim();const r=showBlocks(sess.reply(q));hear(q);return r}
function bpc(text){const st=[new Float32Array(H),new Float32Array(H)];let p=null,tot=0,n=0;const t='س:'+text.slice(0,600)+'\n';
 for(let i=0;i<t.length;i++){const id=cid(t[i]);if(p){tot-=Math.log2(p[id]+1e-9);n++}p=step(id,st)}return n?tot/n:0}
function develop(){const t=memory.slice(-40);return{messages:memory.length,bits:t.length?t.reduce((a,x)=>a+bpc(x),0)/t.length:0,params:PE.length+Wx1.length+Wh1.length+b1.length+Wx2.length+Wh2.length+b2.length+Wo.length+bo.length}}
const P_=()=>({PE,Wx1,Wh1,b1,Wx2,Wh2,b2,Wo,bo});
return{_t:{copyDist,copySource},respondFile,fileBlocks,params:P_,dims:()=>({E:Em,H,V}),chars,setParams:o=>{for(const[k,v]of Object.entries(P_()))if(o[k]&&o[k].length==v.length)v.set(o[k])},respond,develop,newChat:()=>{sess=new Session()},memory:()=>memory,count:()=>memory.length,wipe:()=>{memory=[];saveMem()}}})();
/*ENGINE-END*/
