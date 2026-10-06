import type {Word} from '../types';
export type Series={role:string;id?:string;times:number[];values:(number|null)[];words?:Word[];tokenXs?:number[];showPoints?:boolean};
export function tokenCoordinate(t:number,words:Word[]):number|null{
  const word=words.find(w=>w.start_s!==null&&w.end_s!==null&&t>=w.start_s&&t<=w.end_s);
  return word&&word.start_s!==null&&word.end_s!==null?word.id+(t-word.start_s)/Math.max(.001,word.end_s-word.start_s):null;
}
export function Chart({title,unit,series,normalized=false,selection,onSeek}:{title:string;unit:string;series:Series[];normalized?:boolean;selection?:[number,number]|null;onSeek?:(t:number)=>void}){
  const width=960,height=168,left=54,right=14,top=17,bottom=28;
  const points=series.map(s=>({...s,coordinates:s.times.map((t,i)=>({x:normalized?(s.tokenXs?.[i]??tokenCoordinate(t,s.words||[])):t,y:s.values[i]}))}));
  const xs=points.flatMap(s=>s.coordinates.filter(p=>p.x!==null).map(p=>p.x!));
  const ys=points.flatMap(s=>s.coordinates.filter(p=>p.y!==null&&Number.isFinite(p.y)).map(p=>p.y!));
  const xmax=Math.max(1,...xs),ymin=Math.min(0,...ys),ymax=Math.max(ymin+1,...ys);
  const sx=(v:number)=>left+v/xmax*(width-left-right),sy=(v:number)=>height-bottom-(v-ymin)/(ymax-ymin)*(height-top-bottom);
  const path=(s:typeof points[number])=>{let active=false;return s.coordinates.map((p,i)=>{
    if(p.x===null||p.y===null||!Number.isFinite(p.y)){active=false;return '';}
    const previous=i?s.coordinates[i-1]:null;
    if(previous&&previous.x!==null&&normalized&&p.x-previous.x>1.1)active=false;
    const command=active?'L':'M';active=true;return `${command}${sx(p.x).toFixed(2)},${sy(p.y).toFixed(2)}`;
  }).join(' ');};
  return <section className="chart"><div className="chart-title"><h3>{title}</h3><span>{unit}</span></div>
    <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${title}, ${unit}; ${normalized?'canonical token index':'native seconds'}`} onClick={e=>{
      if(onSeek&&!normalized){const rect=e.currentTarget.getBoundingClientRect();onSeek(Math.max(0,Math.min(xmax,((e.clientX-rect.left)/rect.width*width-left)/(width-left-right)*xmax)));}}}>
      {[0,.5,1].map(v=><g key={v}><line x1={left} x2={width-right} y1={sy(ymin+v*(ymax-ymin))} y2={sy(ymin+v*(ymax-ymin))} stroke="#e5eaf0"/><text x={left-8} y={sy(ymin+v*(ymax-ymin))+4} textAnchor="end">{(ymin+v*(ymax-ymin)).toFixed(1)}</text></g>)}
      {selection&&!normalized&&<rect x={sx(selection[0])} y={top} width={Math.max(2,sx(selection[1])-sx(selection[0]))} height={height-top-bottom} fill="#f2b764" opacity=".2"/>}
      {points.map(s=><path key={s.id||s.role} d={path(s)} fill="none" stroke={s.role==='reference'?'#8295ac':'#087f89'} strokeWidth={s.role==='reference'?1.6:2.1} strokeDasharray={s.role==='reference'?'5 3':undefined}/>)}
      {points.filter(s=>s.showPoints).flatMap(s=>s.coordinates.filter(p=>p.x!==null&&p.y!==null).map((p,i)=><circle key={(s.id||s.role)+i} cx={sx(p.x!)} cy={sy(p.y!)} r={3} fill={s.role==='reference'?'#8295ac':'#087f89'}/>))}
      {[0,.25,.5,.75,1].map(v=><text key={v} x={sx(v*xmax)} y={height-7} textAnchor="middle">{(v*xmax).toFixed(normalized?0:1)}</text>)}
    </svg><p className="axis-label">{normalized?'Canonical token index + progress within word (pauses excluded; see boundary panel)':'Native time in seconds · each recording keeps its own clock'}</p>
  </section>;
}
