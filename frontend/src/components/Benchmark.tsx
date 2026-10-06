import {useEffect,useState} from 'react';
import {api,number} from '../api';
type Count={precision:number|null;recall:number|null;f1:number|null;tp:number;fp:number;fn:number};
type Summary={status:string;metrics:null|{evaluated_recordings:number;held_out_test_macro_f1_tiou_0_5_proxy:number|null;median_spearman_proxy:number|null;localization:Record<string,Record<string,Count>>;runtime:{median_processing_s_per_audio_s:number|null;peak_memory_mb:number|null};explanation_audit:{events_audited:number;all_quote_clock_value_rule_checks_passed:boolean};held_out_generation_method:{n:number;method:string}};robustness:null|{conditions:{condition:string;score:number|null;absolute_score_shift:number|null;coverage:number}[]}};
export function Benchmark(){
 const [data,setData]=useState<Summary|null>(null);
 useEffect(()=>{api<Summary>('/api/evaluation-summary').then(setData).catch(()=>{});},[]);
 const m=data?.metrics;
 return <section className="benchmark" data-testid="benchmark"><h3>Measured evaluation</h3>
 <p>Synthetic intervention supports are localization proxies. Human perceptual accuracy, independent agreement and human generalization remain unmeasured.</p>
 {!m?<p>The full benchmark is pending. No accuracy result is prefilled.</p>:<><p>{m.evaluated_recordings} recordings · held-out test macro F1 at tIoU 0.5: <strong>{number(m.held_out_test_macro_f1_tiou_0_5_proxy,3)}</strong> · median within-family Spearman: <strong>{number(m.median_spearman_proxy,3)}</strong>. Only one independent test speaker; thresholds are frozen engineering tolerances.</p>
 <div className="pause-table"><table><caption>Held-out test events against transformation support, tIoU 0.5</caption><thead><tr><th>Type</th><th>TP / FP / missed</th><th>Precision</th><th>Recall</th><th>F1</th></tr></thead><tbody>{Object.entries(m.localization.test||{}).filter(([k])=>k.startsWith('0.5/')).map(([k,v])=><tr key={k}><td>{k.split('/')[1]}</td><td>{v.tp} / {v.fp} / {v.fn}</td><td>{number(v.precision,3)}</td><td>{number(v.recall,3)}</td><td>{number(v.f1,3)}</td></tr>)}</tbody></table></div>
 <p>Held-out generation method: {m.held_out_generation_method.method}, {m.held_out_generation_method.n} test recordings. Median processing seconds/audio second: {number(m.runtime.median_processing_s_per_audio_s,2)}. Peak process resident memory: {number(m.runtime.peak_memory_mb,0)} MB. Evidence audit: {m.explanation_audit.events_audited} events; quote, clock, numeric value and rule checks {m.explanation_audit.all_quote_clock_value_rule_checks_passed?'passed':'failed'}.</p></>}
 {data?.robustness&&<><h3>Actual fixture stress tests</h3><div className="pause-table"><table><thead><tr><th>Condition</th><th>Score</th><th>Absolute score shift</th><th>Coverage</th></tr></thead><tbody>{data.robustness.conditions.map(c=><tr key={c.condition}><td>{c.condition}</td><td>{number(c.score)}</td><td>{number(c.absolute_score_shift)}</td><td>{number(c.coverage*100)}%</td></tr>)}</tbody></table></div><p>A dash is abstention, not a zero penalty. These are one-fixture stress results, not population guarantees. Full denominators and failures are retained in evaluation/.</p></>}
 </section>;
}
