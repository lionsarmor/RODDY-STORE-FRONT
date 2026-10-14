// Original RODDY emblem: six rounded, outlined ribbons with warm retro colors.
// No SVG strokes, fonts or linked images are needed by the keycap renderer.
import fs from 'node:fs';
const round=n=>Number(n.toFixed(5));
function ribbon(a,b,width,offset){
 const dx=b[0]-a[0],dy=b[1]-a[1],length=Math.hypot(dx,dy),u=[dx/length,dy/length],n=[-u[1],u[0]],r=width/2,k=.5522847498307936;
 a=a.map((x,i)=>x+n[i]*offset);b=b.map((x,i)=>x+n[i]*offset);
 const p=(v,t=0,s=0)=>v.map((x,i)=>round(x+n[i]*t+u[i]*s)).join(' ');
 return `M${p(a,r)}L${p(b,r)}C${p(b,r,k*r)} ${p(b,k*r,r)} ${p(b,0,r)}C${p(b,-k*r,r)} ${p(b,-r,k*r)} ${p(b,-r)}L${p(a,-r)}C${p(a,-r,-k*r)} ${p(a,-k*r,-r)} ${p(a,0,-r)}C${p(a,k*r,-r)} ${p(a,r,-k*r)} ${p(a,r)}Z`;
}
const palette=[{fill:'#DDAB3B',paletteId:'YW026'},{fill:'#F06434',paletteId:'OG001'},{fill:'#C8393A',paletteId:'RD004'}];
const shapes=[];
for(const [a,b] of [[[12,10],[52,54]],[[52,10],[12,54]]]){
 palette.forEach((c,i)=>shapes.push({path:ribbon(a,b,7,(i-1)*9.5),...c}));
}
const mark={label:'Analog X',inspiration:'70s curves · 80s racing stripes',shapes};
const file='src/keycap-artwork/retro-x-marks.json';const marks=JSON.parse(fs.readFileSync(file));marks['analog-x']=mark;fs.writeFileSync(file,JSON.stringify(marks,null,2)+'\n');
const art=shapes.map(s=>`<path d="${s.path}" fill="${s.fill}"/>`).join('');
fs.writeFileSync('src/keycap-artwork/retro-x/analog-x.svg',`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><title>RODDY Analog X</title><desc>Original rounded six-ribbon X in mustard, orange and brick red. Native outlined geometry.</desc>${art}</svg>\n`);
const cards=[{x:40,color:'#F7F7F5',label:'OFF-WHITE'},{x:360,color:'#7FAFD3',label:'V6 BLUE'},{x:680,color:'#50545E',label:'CHARCOAL'}];
fs.writeFileSync('src/keycap-artwork/retro-x/analog-x-preview.svg',`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 420" width="1000" height="420"><rect width="1000" height="420" fill="#17181C"/><g font-family="Arial,sans-serif" fill="#F7F7F5"><text x="40" y="52" font-size="25" font-weight="bold" letter-spacing="2">RODDY / ANALOG X</text><text x="40" y="82" font-size="15">70s curves. 80s racing stripes. One original signal.</text>${cards.map(c=>`<rect x="${c.x}" y="115" width="280" height="240" rx="26" fill="${c.color}"/><svg x="${c.x+40}" y="132" width="200" height="200" viewBox="0 0 64 64">${art}</svg><text x="${c.x}" y="389" font-size="12" letter-spacing="2">${c.label}</text>`).join('')}</g></svg>\n`);
console.log('Built Analog X SVG and keycap comparison from six closed ribbon paths.');
